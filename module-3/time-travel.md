# Time travel

## Review

人間が関与する(human-in-the-loop)理由について説明しました:

(1) `承認` - エージェントを中断して、ユーザーに状態を知らせ、ユーザーがアクションを受け入れられるようにすることができます

(2) `デバッグ` - グラフを巻き戻して問題を再現または回避することができます

(3) `編集` - 状態を変更できます

ブレークポイントによって特定のノードでグラフを停止したり、グラフが動的に中断したりする方法を示しました。

次に、人間の承認で続行する方法、または人間のフィードバックを使用してグラフの状態を直接編集する方法を示しました。

## Goals

次に、過去の状態を表示、再生、さらにはフォークすることで、LangGraph が [デバッグをサポート](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/time-travel/) する方法を示しましょう。

これを `タイムトラベル` と呼びます。


エージェントを構築しましょう。

前と同じように実行してみましょう。

## Browsing history

`thread_id` がわかれば、`get_state` を使用してグラフの **現在の** 状態を確認できます。

エージェントの状態履歴を参照することもできます。

`get_state_history` を使用すると、以前のすべてのステップの状態を取得できます。

最初の要素は、`get_state` から取得した現在の状態です。

上記のすべてをここで視覚化します:

![fig1.jpg](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66dbb038211b544898570be3_time-travel1.png)


## Replaying

以前のステップのいずれかからエージェントを再実行できます。

![fig2.jpg](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66dbb038a0bd34b541c78fb8_time-travel2.png)

人間の入力を受けたステップを振り返ってみましょう。

stateを見てください

次に呼び出すノードを確認できます。

また、`checkpoint_id` と `thread_id` を示す構成も取得します。

ここから再生するには、構成をエージェントに返すだけです!

graphは、このチェックポイントがすでに実行されていることを認識しています。

このチェックポイントから再生するだけです!

これで、エージェントが再実行された後の現在の状態を確認できます。

## Forking

同じステップから実行したいが、入力は異なる場合はどうなるでしょうか。

これがフォークです。

![fig3.jpg](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66dbb038f89f2d847ee5c336_time-travel3.png)

もう一度、設定を行います。

このチェックポイントでstateを変更してみましょう。

`checkpoint_id` を指定して `update_state` を実行するだけです。

`messages` のリデューサーの動作を思い出してください:

* メッセージ ID を指定しない限り、追加されます。
* 状態に追加するのではなく、メッセージを上書きするためにメッセージ ID を指定します!

したがって、メッセージを上書きするには、`to_fork.values["messages"].id` にあるmessage ID を指定します。

これにより、新しいフォークされたチェックポイントが作成されます。

ただし、メタデータ (次に進む場所など) は保持されます。

エージェントの現在の状態がフォークによって更新されたことがわかります。

ここで、ストリーミングすると、グラフはこのチェックポイントがまだ実行されていないことを認識します。

したがって、単に再生するのではなく、グラフが実行されます。

ここで、現在の状態がエージェントの実行の終了であることがわかります。

### Time travel with LangGraph API

--

**⚠️ 免責事項**

*Studio を実行するには、現在 Mac が必要です。Mac を使用していない場合は、この手順をスキップしてください。*

*また、このノートブックを CoLab で実行している場合は、この手順をスキップしてください。*

--

`module-3/studio/langgraph.json` に設定されている `module-3/studio/agent.py` を使用する Studio UI に `agent` をロードしましょう。

![Screenshot 2024-08-26 at 9.59.19 AM.png](https://cdn.prod.website-files.com/65b8cd72835ceeacd4449a53/66dbb038211b544898570bec_time-travel4.png)

SDK 経由で接続し、LangGraph API が [タイムトラベルをサポート](https://langchain-ai.github.io/langgraph/cloud/how-tos/human_in_the_loop_time_travel/#initial-invocation) する方法を示します。

#### Re-playing
各ノードが呼び出された後、グラフの状態に `updates` をストリーミングするエージェントを実行してみましょう。

ここで、指定されたチェックポイントからの**replaying**を見てみましょう。

`checkpoint_id` を渡すだけです。

再生時に各ノードの完全な状態を確認するには、`stream_mode="values"` でストリーミングしてみましょう。

これは、応答するノードによって行われた状態への `updates` のみをストリーミングするものと見なすことができます。

#### Forking

フォークについて見てみましょう。

上で作業したのと同じ手順、つまり人間の入力を取得してみましょう。

エージェントを使用して新しいスレッドを作成しましょう。

状態を編集してみましょう。

`messages` のリデューサーがどのように動作するかを思い出してください:

* メッセージ ID を指定しない限り、追加されます。
* 状態に追加するのではなく、メッセージを上書きするためにメッセージ ID を指定します。

再実行するには、`checkpoint_id` を渡します。

### LnagGraph Studio
`module-1/studio/langgraph.json` に設定されている `module-1/studio/agent.py` を使用する `agent` を使用して Studio UI でフォークする様子を見てみましょう。