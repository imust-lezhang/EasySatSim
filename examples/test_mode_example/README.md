# Test Mode Example

This example demonstrates EasySatSim's two-user test mode with the live
visualization interface. It uses an independent Starlink Phase I-A configuration
containing 1,600 satellites and two fixed users located in Beijing and Tokyo.
Packets use the normal satellite path rather than the direct-connection mode.

Run the example from the project root:

```powershell
python -m examples.test_mode_example.main
```

The same `main.py` can also be run directly from PyCharm. The entry script
locates the project root itself, so it does not depend on PyCharm's working
directory or source-root settings.

The example creates a timestamped CSV file under
`examples/test_mode_example/output/`. Its configuration is local to this
example and does not change the main simulator configuration. The generated
CSV files are local runtime artifacts and are not included in the repository.

This is a focused functional demonstration, not a paper case study or a
performance benchmark.
