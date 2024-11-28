# Chatbot with message summarization & external DB memory

## Review 

graph state schemaとreducerのカスタマイズ方法について学んできました。

また、graph stateでメッセージをトリミングやフィルタリングするための様々なテクニックも見てきました。

これらの概念を会話の要約を生成するメモリ付きチャットボットで使用しました。

## Goals

しかし、チャットボットに無期限に持続するメモリを持たせたい場合はどうすればよいでしょうか?

ここでは、外部データベースをサポートするより高度なチェックポインターを紹介します。

ここでは[Sqliteをチェックポインターとして使用する方法](https://langchain-ai.github.io/langgraph/concepts/low_level/#checkpointer)を紹介しますが、[Postgres](https://langchain-ai.github.io/langgraph/how-tos/persistence_postgres/)のような他のチェックポインターも利用可能です!

## Sqlite

ここでの良い出発点は[SqliteSaverチェックポインター](https://langchain-ai.github.io/langgraph/concepts/low_level/#checkpointer)です。

Sqliteは[小型で高速、非常に人気のある](https://x.com/karpathy/status/1819490455664685297) SQLデータベースです。

`:memory:`を指定すると、メモリ上にSqliteデータベースを作成します。

データベースのパスを指定すると、データベースを作成してくれます!

チャットボットを再定義しましょう。

ここで、sqlite チェックポインターを使用して再コンパイルします。

これで、グラフを複数回呼び出すことができます。

状態がローカルに保存されていることを確認しましょう。

### 状態の永続化

データベースとしてSqliteを使用することは、状態が永続化されることを意味します!

例えば、ノートブックカーネルを再起動しても、ディスク上のSqlite DBから読み込めることを確認できます。

## LangGraph Studio 

--

**⚠️ 免責事項**

*Studioの実行には現在Macが必要です。Macを使用していない場合は、このステップをスキップしてください。*

--

外部メモリについてより理解が深まったところで、LangGraph APIがコードをパッケージ化し、組み込みの永続化を提供していることを思い出してください。

そしてAPIはStudioのバックエンドです!

`module2-/studio/langgraph.json`で設定された`module2-/studio/chatbot.py`を使用する`chatbot`をUIに読み込みます。
