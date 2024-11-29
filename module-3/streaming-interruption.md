# Streaming 

## Review

モジュール 2 では、graph stateとメモリをカスタマイズするいくつかの方法について説明しました。

長時間の会話を維持できる外部メモリを備えたチャットボットを構築しました。

## Goals

このモジュールでは、メモリを基盤としてユーザーがさまざまな方法でグラフと直接対話できるようにする「ヒューマンインザループ」について詳しく説明します。

「ヒューマンインザループ」の準備として、まずストリーミングについて詳しく説明します。ストリーミングでは、実行中にグラフ出力 (ノードの状態やチャット モデル トークンなど) を視覚化する方法がいくつか提供されます。

## Streaming

LangGraph は、[ストリーミングのファーストクラス サポート](https://langchain-ai.github.io/langgraph/concepts/low_level/#streaming) で構築されています。

モジュール 2 からチャットボットを設定し、実行中にグラフから出力をストリーミングするさまざまな方法を示しましょう。

トークン単位のストリーミングを有効にするために、`call_model` で `RunnableConfig` を使用していることに注意してください。これは [python < 3.11 でのみ必要](https://langchain-ai.github.io/langgraph/how-tos/streaming-tokens/) です。このノートブックを CoLab で実行している場合に備えて、python 3.x を使用します。

## Streaming full state

[グラフの状態をストリーミングする](https://langchain-ai.github.io/langgraph/concepts/low_level/#streaming)方法について説明します。

`.stream` と `.astream` は、結果をストリーミングで返すための同期メソッドと非同期メソッドです。

LangGraph は、[グラフの状態](https://langchain-ai.github.io/langgraph/how-tos/stream-values/) に対していくつかの [異なるストリーミング モード](https://langchain-ai.github.io/langgraph/how-tos/stream-values/) をサポートしています。

* `values`: これは、各ノードが呼び出された後にグラフの完全な状態をストリーミングします。

* `updates`: これは、各ノードが呼び出された後にグラフの状態への更新をストリーミングします。

![values_vs_updates.png](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66dbaf892d24625a201744e5_streaming1.png)

`stream_mode="updates"` を見てみましょう。

`updates` を使用してストリーミングするため、グラフ内のノードが実行された後の状態の更新のみが表示されます。

各 `chunk` は、`node_name` をキーとし、更新された状態を値とする辞書です。

それでは、状態の更新を印刷してみましょう。

ここで、`stream_mode="values"` が表示されます。

これは、`conversation` ノードが呼び出された後のグラフの `full state` です。

## Streaming tokens

多くの場合、グラフの状態以上のものをストリーミングする必要があります。

特に、チャット モデルの呼び出しでは、トークンが生成されるたびにストリーミングするのが一般的です。

[`.astream_events` メソッド](https://langchain-ai.github.io/langgraph/how-tos/streaming-from-final-node/#stream-outputs-from-the-final-node) を使用してこれを行うことができます。このメソッドは、ノード内で発生するイベントをストリーミングで返します。

各イベントはいくつかのキーを持つdictです：
 
* `event`: 発生しているイベントのタイプ
* `name`: イベントの名前
* `data`: イベントに関連付けられたデータ
* `metadata`: イベントを発行するノードである `langgraph_node` が含まれます。

見てみよう。

重要な点は、グラフ内のチャット モデルのトークンが `on_chat_model_stream` タイプであることです。

`event['metadata']['langgraph_node']` を使用して、ストリーミング元のノードを選択できます。

また、`event['data']` を使用して、各イベントの実際のデータ (この場合は `AIMessageChunk`) を取得できます。

上記のように、`AIMessageChunk` を取得するには `chunk` キーを使用するだけです。

## Streaming with LangGraph API

**⚠️ 免責事項**

*Studio を実行するには、現在 Mac が必要です。Mac を使用していない場合は、この手順をスキップしてください。*

*また、このノートブックを CoLab で実行している場合は、この手順をスキップしてください。*

--

LangGraph API は [ストリーミングのファーストクラス サポートを備えています](https://langchain-ai.github.io/langgraph/cloud/concepts/api/#streaming)。

Studio UI に `agent` をロードしましょう。これは、`module-3/studio/langgraph.json` に設定されている `module-3/studio/agent.py` を使用します。

LangGraph API は、Studio のバックエンドとして機能します。

LangGraph SDK を介して LangGraph API と直接やり取りできます。

Studio からローカル デプロイメントの URL を取得するだけです。

先ほどと同じように、[`values`](https://langchain-ai.github.io/langgraph/cloud/how-tos/stream_values/)をストリーミングしてみましょう。

ストリームされたオブジェクトには次のものがあります:

* `event`: タイプ
* `data`: 状態

API 経由でのみサポートされる新しいストリーミング モードがいくつかあります。

たとえば、[`messages` モードを使用](https://langchain-ai.github.io/langgraph/cloud/how-tos/stream_messages/) すると、上記のケースをより適切に処理できます。

このモードでは現在、グラフにメッセージのリストである `messages` キーがあることを前提としています。

`messages` モードを使用して発行されるすべてのイベントには、次の 2 つの属性があります。

* `event`: これはイベントの名前です。
* `data`: これはイベントに関連付けられたデータです。

いくつかのイベントが表示されます:

* `metadata`: 実行に関するメタデータ
* `messages/complete`: 完全な形式のメッセージ
* `messages/partial`: チャット モデル トークン

[こちら](https://langchain-ai.github.io/langgraph/cloud/concepts/api/#modemessages) で、タイプについてさらに詳しく調べることができます。

では、これらのメッセージをストリーミングする方法を示しましょう。

メッセージ内のツール呼び出しのフォーマットを改善するヘルパー関数を定義します。