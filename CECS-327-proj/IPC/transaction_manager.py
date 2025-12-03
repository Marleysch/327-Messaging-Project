import threading
from enum import Enum, auto
from typing import Any, Dict, Optional, Set, Tuple
from IPC.lamport_clock import LamportClock



class TxStatus(Enum):
    ACTIVE = auto()
    COMMITTED = auto()
    ABORTED = auto()


class LockMode(Enum):
    SHARED = "S"
    EXCLUSIVE = "X"


class Lock:
    def __init__(self) -> None:
        self.mode: Optional[LockMode] = None
        self.owners: Set[str] = set()
        self.waiting: list[Tuple[str, LockMode]] = []
        self._cond = threading.Condition()


class Transaction:
    def __init__(self, tx_id: str, start_ts: int) -> None:
        self.tx_id = tx_id
        self.start_ts = start_ts  # Lamport timestamp
        self.status = TxStatus.ACTIVE
        # Local write buffer: key -> new_value
        self.write_set: Dict[str, Any] = {}
        # Undo log for rollback: key -> (existed_before, old_value)
        self.undo_log: Dict[str, Tuple[bool, Any]] = {}
        # Keys this tx currently holds locks on
        self.locked_keys: Set[str] = set()

    def __repr__(self) -> str:
        return f"<Tx {self.tx_id} {self.status.name}>"


class TransactionManager:

    def __init__(self, node_id: str, replica_apply_callback=None) -> None:
        self.node_id = node_id
        self.clock = LamportClock(node_id=node_id)
        self._store: Dict[str, Any] = {}          # committed key-value store
        self._locks: Dict[str, Lock] = {}         # key -> Lock
        self._transactions: Dict[str, Transaction] = {}  # tx_id -> Transaction
        self._lock = threading.RLock()
        self._replica_apply_callback = replica_apply_callback

    def begin(self) -> str:
        with self._lock:
            ts = self.clock.tick()
            tx_id = f"{self.node_id}-{ts}"
            tx = Transaction(tx_id, start_ts=ts)
            self._transactions[tx_id] = tx
            return tx_id

    def read(self, tx_id: str, key: str) -> Any:
        tx = self._require_active(tx_id)

        # If the transaction has already written to this key, return
        # its buffered value (read-your-own-writes).
        if key in tx.write_set:
            return tx.write_set[key]

        self._acquire_lock(tx, key, LockMode.SHARED)
        with self._lock:
            return self._store.get(key)

    def write(self, tx_id: str, key: str, value: Any) -> None:
        tx = self._require_active(tx_id)

        self._acquire_lock(tx, key, LockMode.EXCLUSIVE)

        with self._lock:
            # Only log the original value the first time this tx writes key
            if key not in tx.undo_log:
                if key in self._store:
                    tx.undo_log[key] = (True, self._store[key])
                else:
                    tx.undo_log[key] = (False, None)

            tx.write_set[key] = value

    def commit(self, tx_id: str) -> bool:
        tx = self._require_active(tx_id)

        with self._lock:
            # Apply buffered writes to the shared store atomically
            for key, value in tx.write_set.items():
                self._store[key] = value

            commit_ts = self.clock.tick()
            tx.status = TxStatus.COMMITTED

            # Propagate to other replicas if a callback is configured
            if self._replica_apply_callback is not None:
                try:
                    self._replica_apply_callback(tx.tx_id, dict(tx.write_set), commit_ts)
                except Exception as e:
                    # We do not roll back the local commit here, but we log the error.
                    print(f"[TxManager] Replica apply failed for {tx_id}: {e}")

            # Release all locks held by this transaction
            self._release_all_locks(tx)

            return True

    def abort(self, tx_id: str) -> None:
        tx = self._transactions.get(tx_id)
        if tx is None:
            return

        with self._lock:
            # Roll back: restore original values using the undo log
            for key, (existed, old_value) in tx.undo_log.items():
                if existed:
                    self._store[key] = old_value
                elif key in self._store:
                    # Key was newly created by this tx
                    del self._store[key]

            tx.status = TxStatus.ABORTED
            self._release_all_locks(tx)

    def apply_replica_commit(self, tx_id: str, write_set: Dict[str, Any], commit_ts: int) -> None:
        with self._lock:
            self.clock.update(commit_ts)
            for key, value in write_set.items():
                self._store[key] = value

            # We track the remote transaction for observability
            tx = Transaction(tx_id, start_ts=commit_ts)
            tx.status = TxStatus.COMMITTED
            self._transactions[tx_id] = tx

    def dump_store(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._store)

    def get_status(self, tx_id: str) -> Optional[TxStatus]:
        tx = self._transactions.get(tx_id)
        return tx.status if tx is not None else None


    def _require_active(self, tx_id: str) -> Transaction:
        with self._lock:
            tx = self._transactions.get(tx_id)
            if tx is None:
                raise KeyError(f"Unknown transaction {tx_id}")
            if tx.status is not TxStatus.ACTIVE:
                raise RuntimeError(f"Transaction {tx_id} not ACTIVE ({tx.status})")
            return tx

    def _get_lock(self, key: str) -> Lock:
        with self._lock:
            if key not in self._locks:
                self._locks[key] = Lock()
            return self._locks[key]

    def _acquire_lock(self, tx: Transaction, key: str, mode: LockMode) -> None:
        lock = self._get_lock(key)

        while True:
            with lock._cond:
                # Fast path: lock is free
                if lock.mode is None:
                    lock.mode = mode
                    lock.owners.add(tx.tx_id)
                    tx.locked_keys.add(key)
                    return

                # Shared lock request and current mode is SHARED:
                # compatible if no owners are in conflict with upgrade.
                if mode == LockMode.SHARED and lock.mode == LockMode.SHARED:
                    # multiple readers allowed
                    lock.owners.add(tx.tx_id)
                    tx.locked_keys.add(key)
                    return

                # Otherwise, we need EXCLUSIVE and someone else holds the lock.
                # Check wait-die condition against the *oldest* conflicting owner.
                oldest_owner_ts = None
                oldest_owner_tx_id = None
                for owner_id in lock.owners:
                    owner = self._transactions.get(owner_id)
                    if owner is None:
                        continue
                    if oldest_owner_ts is None or owner.start_ts < oldest_owner_ts:
                        oldest_owner_ts = owner.start_ts
                        oldest_owner_tx_id = owner.tx_id

                # If this transaction is *younger* than the oldest owner, it dies (aborts)
                if oldest_owner_ts is not None and tx.start_ts > oldest_owner_ts:
                    # Abort and raise so caller can surface the conflict
                    print(f"[TxManager] wait-die: aborting younger tx {tx.tx_id} "
                          f"waiting for older {oldest_owner_tx_id}")
                    self.abort(tx.tx_id)
                    raise RuntimeError(f"Transaction {tx.tx_id} aborted by wait-die policy")

                # Otherwise this transaction is older; it may wait
                lock.waiting.append((tx.tx_id, mode))
                lock._cond.wait()

                # When notified, loop and re-evaluate

    def _release_all_locks(self, tx: Transaction) -> None:
        for key in list(tx.locked_keys):
            lock = self._locks.get(key)
            if lock is None:
                continue
            with lock._cond:
                if tx.tx_id in lock.owners:
                    lock.owners.remove(tx.tx_id)

                # If no owners remain, free the lock and wake up waiters
                if not lock.owners:
                    lock.mode = None
                    # Wake up everyone; they will re-check compatibility
                    lock._cond.notify_all()

        tx.locked_keys.clear()
