# doc-loader

#### Diverse Types Doc Links

* https://docs.openvino.ai/2023.3/openvino_docs_install_guides_installing_openvino_pip.html#
* https://docs.openvino.ai/2023.3/openvino_docs_install_guides_configurations_for_intel_gpu.html#
* https://docs.openvino.ai/2023.3/system_requirements.html#
* https://docs.openvino.ai/2023.3/openvino_docs_OV_UG_Infer_request.html#
* https://docs.openvino.ai/2023.3/openvino_docs_deploy_local_distribution.html#
* https://docs.openvino.ai/2023.3/api/ie_python_api/_autosummary/openvino.runtime.op.Constant.html#
* https://docs.openvino.ai/2023.3/openvino_release_notes.html#
* https://docs.openvino.ai/2023.3/openvino_docs_performance_benchmarks.html#

Advanced:
* https://docs.openvino.ai/2023.3/openvino_sample_hello_classification.html


```bash
wget https://docs.openvino.ai/2023.3/openvino_docs_install_guides_installing_openvino_pip.html
```

```
metadata={'source': 'https://docs.openvino.ai/2023.3/openvino_docs_install_guides_installing_openvino_pip.html', 'title': 'Install Intel® Distribution of OpenVINO™ Toolkit from PyPI Repository — OpenVINO™  documentation', 'description': 'Learn how to install OpenVINO™ Runtime on Windows, Linux, and macOS operating systems, using a PyPi package.', 'language': 'en'})]

<meta name="docsearch:language" content="en">
```

```bash
huggingface-cli login
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

huggingface-cli delete-cache
```

```bash
vi /home/codespace/.python/current/lib/python3.10/site-packages/chromadb/__init__.py 

# add below to top of file
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
```

```bash
python -m spacy download en_core_web_sm
python -m spacy download en_core_web_trf
```
```bash
python process_docs_multicore.py --emodel 'sentence-transformers/all-mpnet-base-v2'
python rag_cli_infer.py --storedir 'VectorStores/20240129_013709' --modelid 'helenai/gpt2-ov'
```

```bash
wget https://docs.openvino.ai/archives/2023.3.zip
unzip 2023.2.zip
python -m venv openvino_env
source openvino_env/bin/activate
```
```bash
python rag_cli_infer.py --storedir VectorStores/20240129_171328 --modelid ov_model

optimum-cli export openvino --model Intel/neural-chat-7b-v3-3 ov_model
du -h --max-depth=1
huggingface-cli scan-cache

 optimum-cli export openvino -m 'Intel/neural-chat-7b-v3-1' --trust-remote-code --weight-format int4_sym_g64 --task text-generation INT4

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
```