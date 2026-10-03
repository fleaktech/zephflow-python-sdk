# ZephFlow Python SDK (deprecated)

**This package is deprecated and no longer maintained.**

The ZephFlow Python SDK is a thin wrapper around the ZephFlow Java SDK (`io.fleak.zephflow:sdk`). The Java SDK is removed in ZephFlow 0.5.0, so this package will not get new releases.

- Releases already on [PyPI](https://pypi.org/project/zephflow/) keep working: they download the Java SDK jar of the version they were built for (currently 0.3.1) from the [zephflow-core GitHub releases](https://github.com/fleaktech/zephflow-core/releases), which stay available.
- For new pipelines, define the DAG in YAML and run it with the ZephFlow CLI starter (Docker image `fleak/zephflow-clistarter`). See [Running ZephFlow as a Standalone Process with CLI Starter](https://docs.fleak.ai/zephflow/getting-started#running-zephflow-as-a-standalone-process-with-cli-starter).

The previous README, with the full API documentation, is in the git history of this repository.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
