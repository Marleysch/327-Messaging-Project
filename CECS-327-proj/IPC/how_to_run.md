# How to run?

### Example with 2 nodes

Open 2 terminal windows.

In terminal 1, run:

```bash
python3 p2p_node.py 1 127.0.0.1:7898
```
```
```

In terminal 2, run:

```bash
python3 p2p_node.py 2 127.0.0.1:7897
```
```

### Example with 3 nodes

Open 3 terminal windows.

In terminal 1, run:

```bash
python3 p2p_node.py 1 127.0.0.1:7898 127.0.0.1:7899
```

In terminal 2, run:

```bash
python3 p2p_node.py 2 127.0.0.1:7897 127.0.0.1:7899
```

In terminal 3, run:

```bash
python3 p2p_node.py 3 127.0.0.1:7897 127.0.0.1:7898
```
```
```
```
