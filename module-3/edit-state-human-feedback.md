# Editing graph state

## Review

human-in-the-loopの動機について説明しました:

(1) 「承認」 - エージェントを中断して、ユーザーに状態を表示し、ユーザーがアクションを受け入れられるようにすることができます

(2) 「デバッグ」 - グラフを巻き戻して問題を再現または回避することができます

(3) 「編集」 - 状態を変更できます

ブレークポイントがユーザー承認をサポートする方法を示しましたが、グラフが中断された後にグラフの状態を変更する方法はまだわかりません。

## Goals

ここで、グラフの状態を直接編集し、人間によるフィードバックを挿入する方法を説明します。

## Editin state

以前、ブレークポイントを紹介しました。

ブレークポイントを使用してグラフを中断し、次のノードを実行する前にユーザーの承認を待ちました。

ただし、ブレークポイントは [グラフの状態を変更する機会](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/edit-graph-state/) でもあります。

`assistant` ノードの前にブレークポイントを設定してエージェントを設定しましょう。

実行してみましょう!

チャット モデルが応答する前にグラフが中断されていることがわかります。

これで、状態の更新を直接適用できます。

`messages` キーの更新では `add_messages` リデューサーが使用されることに注意してください。

* 既存のメッセージを上書きする場合は、メッセージの `id` を指定できます。
* メッセージのリストに追加するだけの場合は、以下に示すように、`id` を指定せずにメッセージを渡すことができます。

見てみましょう。

新しいメッセージで `update_state` を呼び出しました。

`add_messages` リデューサーはそれを状態キー `messages` に追加します。

さて、エージェントを進めましょう。単に `None` を渡して、現在の状態から進めます。

現在の状態を出力してから、残りのノードの実行に進みます。

これで、`breakpoint` がある `assistant` に戻ります。

再度 `None` を渡して続行できます。

## Editing graph state in Studio

--

**⚠️ 免責事項**

*Studio を実行するには、現在 Mac が必要です。Mac を使用していない場合は、この手順をスキップしてください。*

*また、このノートブックを CoLab で実行している場合は、この手順をスキップしてください。*

--

`module-3/studio/langgraph.json` に設定されている `module-3/studio/agent.py` を使用する Studio UI に `agent` をロードしましょう。

### Editing graph state with LangGraph API

SDK を介してエージェントと対話できます。

![Screenshot 2024-08-26 at 9.59.19 AM.png](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66dbaf2fbfb576f8e53ed930_edit-state-human-feedback1.png)

Studio からローカル デプロイメントの URL を取得しましょう。

LangGraph API は [グラフ状態の編集をサポート](https://langchain-ai.github.io/langgraph/cloud/how-tos/human_in_the_loop_edit_state/#initial-invocation)

私たちのエージェントは `assistant/agent.py` で定義されています。

コードを見ると、ブレークポイントがないことがわかります。

もちろん、`agent.py` に追加することもできますが、API の非常に優れた機能の 1 つは、ブレークポイントを渡すことができることです。

ここでは、`interrupt_before=["assistant"]` を渡します。

現在の状態を知ることができます

状態の最後のメッセージを見ることができます。

編集できます！

前に述べたように、`messages` キーの更新では同じ `add_messages` リデューサーが使用されることに注意してください。

既存のメッセージを上書きする場合は、メッセージの `id` を指定できます。

ここでは、それを実行しました。上記のように、メッセージの `content` のみを変更しました。

ここで、`None` を渡して再開します。

予想どおり、ツール呼び出しの結果は `9` になります。

## Awaiting user input

したがって、ブレークポイント後にエージェントの状態を編集できることは明らかです。

では、この状態の更新を実行するために人間のフィードバックを許可する場合はどうでしょうか?

エージェント内に [人間のフィードバックのプレースホルダーとして機能する](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/wait-user-input/#setup) ノードを追加します。

この `human_feedback` ノードにより、ユーザーは状態に直接フィードバックを追加できます。

`human_feedback` ノードの `interrupt_before` を使用してブレークポイントを指定します。

このノードまでのグラフの状態を保存するためにチェックポインターを設定します。

ユーザーからのフィードバックを取得します。

以前と同様に、`.update_state` を使用して、取得した人間の応答でグラフの状態を更新します。

`as_node="human_feedback"` パラメータを使用して、指定されたノード `human_feedback` としてこの状態更新を適用します。