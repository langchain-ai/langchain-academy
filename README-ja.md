# オレオレ設定

requirementst.txt は使っていません。
reqirements_freeze_20240911.txt は、ファイル名通り 2024/09/11 時点でのpip install -r requirements.txt のあと pip freeze したものです。
langchian v0.2系であることに注意して下さい。

バージョン指定なしでpip install すると、実行時の最新版になるので、壊れている可能性があることは、皆様御存知のとおりです。
なので、devcontainer + poetryを導入しています。
仮想環境は、`lc-academy-env` ではなく、 poetryのデフォルトの `.venv` (コンテナ内の絶対バスで言うと `/app/.venv`)になります。
sqlite3 はコンテナにインストール済みです。

2024/09/22時点での最新版で動作させて遊んでいます。
langchain 0.3系なので、そんなに古くないです。

`module-0/basics.ipynb` 等のもともと存在するファイルには手を加えていません。
`module-0/basics_ja.ipynb` は、私が動かした時点で勝手に翻訳したものです。
