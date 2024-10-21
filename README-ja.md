# オレオレ設定

requirementst.txt は使っていません。
reqirements_freeze_20240911.txt は、ファイル名通り 2024/09/11 時点でのpip install -r requirements.txt のあと pip freeze したものです。
langchian v0.2系であることに注意して下さい。

バージョン指定なしでpip install すると、実行時の最新版になるので、壊れている可能性があることは、皆様御存知のとおりです。


なので、uv を導入しています。
`uv sync` で `.venv` フォルダができる想定です。
sqlite3 は各自インストールして下さい。OSXなら、 `brew install sqlite3` でインストールできます。


2024/10/21時点での最新版で動作させて遊んでいます。
langchain 0.3系なので、そんなに古くないです。

補足
昔は、devcontainer + poetryで環境構築していましたが、LangGraph StudioがOSXのみ対応(Linux非対応)なので、OSX推奨です。

`module-0/basics.ipynb` 等のもともと存在するファイルには手を加えていません。
`module-0/01_basics_ja.ipynb` 等は、私が動かした時点で勝手に翻訳したものです。
