# Breakpoint

## Review

`human-in-the-loop` では、実行中のグラフ出力を確認したいことがよくあります。

ストリーミングでこの基礎を築きました。

## Goals

`human-in-the-loop` の動機についてお話ししましょう

(1) `承認` - エージェントを中断して、ユーザーに状態を表示し、ユーザーがアクションを受け入れることができる

(2) `デバッグ` - グラフを巻き戻して問題を再現または回避できる

(3) `編集` - 状態を変更できる

LangGraph は、さまざまな `human-in-the-loop` ワークフローをサポートするために、エージェントの状態を取得または更新するいくつかの方法を提供しています。

まず、[ブレークポイント](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/breakpoints/#simple-usage) を紹介します。これは、特定のステップでグラフを停止する簡単な方法を提供します。

これがユーザーの `承認` を可能にする方法を示します。

## Breakpoint for human approval

モジュール 1 で使用した単純なエージェントをもう一度考えてみましょう。

ツールの使用について懸念があると仮定します。エージェントが任意のツールを使用することを許可します。

必要なのは、`interrupt_before=["tools"]` を使用してグラフをコンパイルすることだけです。ここで、`tools` はツール ノードです。

つまり、ツール呼び出しを実行するノード `tools` の前に実行が中断されます。

状態を取得し、次に呼び出すノードを確認できます。

これは、グラフが中断されたことを確認するのに便利な方法です。

ここで、便利なトリックを紹介します。

`None` でグラフを呼び出すと、最後の状態チェックポイントから続行されます。

![breakpoints.jpg](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66dbae7985b747dfed67775d_breakpoints1.png)

わかりやすくするために、LangGraph は、ツール呼び出しで `AIMessage` を含む現在の状態を再発行します。

次に、ツール ノードから始まるグラフ内の次の手順を実行します。

このツール呼び出しでツール ノードが実行され、最終的な回答のためにチャット モデルに渡されることがわかります。

ここで、これらを、ユーザー入力を受け入れる特定のユーザー承認ステップと組み合わせてみましょう。

## Breakpoint with LangGraph API

--

**⚠️ 免責事項**

*Studio を実行するには、現在 Mac が必要です。Mac を使用していない場合は、この手順をスキップしてください。*

*また、このノートブックを CoLab で実行している場合は、この手順をスキップしてください。*

--

`module-3/studio/langgraph.json` に設定されている `module-3/studio/agent.py` を使用する Studio UI に `agent` をロードしましょう。

Studio からローカル デプロイメントの URL を取得しましょう。

![Screenshot 2024-08-26 at 9.36.41 AM.png](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66dbae7989b1d60204c199dc_breakpoints2.png)

LangGraph API は [ブレークポイントをサポートしています](https://langchain-ai.github.io/langgraph/cloud/how-tos/human_in_the_loop_breakpoint/#sdk-initialization)

上記のように、Studio で実行されているグラフをコンパイルするときに、`interrupt_before=["node"]` を追加できます。

ただし、API を使用すると、`interrupt_before` をストリーム メソッドに直接渡すこともできます。

これで、`thread_id` と `None` を入力として渡すことで、以前と同じようにブレークポイントから続行できます。