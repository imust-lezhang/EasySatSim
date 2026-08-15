# Runtime Output

The default EasySatSim application writes timestamped simulation results,
screenshots, and exported run packages to this directory.

These files describe a local run and are not tracked by Git. They may contain
machine-specific paths or configuration snapshots and can grow substantially
across repeated simulations. Copy any result needed for a paper or long-term
archive to a deliberately managed reference-results location or external
release archive before cleaning this directory.

Case-specific paper results are managed under each `cases/case*/experiment/`
and `cases/case*/plotting/` tree. Those directories are not globally ignored;
their contents must be reviewed individually for reproducibility and release.
