# State Reducers

## Review

LangGraphの状態スキーマを定義する方法として、`TypedDict`、`Pydantic`、`Dataclasses`といういくつかの異なる方法を説明しました。

## Goals

今回は、状態スキーマの特定のキー/チャネルにおける状態の更新方法を指定するreducerについて深く掘り下げていきます。

## Default overwriting state

`TypedDict`を状態スキーマとして使ってみましょう。

[コードブロックについては原文のまま]

状態の更新`return {"foo": state['foo'] + 1}`を見てみましょう。

前述のように、デフォルトではLangGraphは状態を更新する好ましい方法を知りません。

そのため、ノード1では`foo`の値を単純に上書きします：

```
return {"foo": state['foo'] + 1}
``` 

入力として`{'foo': 1}`を渡すと、グラフから返される状態は`{'foo': 2}`になります。

## Branching

ノードが分岐するケースを見てみましょう。

問題が発生しました！

ノード1がノード2と3に分岐します。

ノード2と3はグラフの同じステップで並列に実行されます。

両方のノードが同じステップ内で状態を上書きしようとします。

これはグラフにとって曖昧です!どちらの状態を保持すべきでしょうか?


## Reducers

[Reducers](https://langchain-ai.github.io/langgraph/concepts/low_level/#reducers) は、この問題に対処する一般的な方法を提供します。

更新の実行方法を指定します。

`Annotated` 型を使用してリデューサー関数を指定できます。 

たとえば、この場合、各ノードから返された値を上書きするのではなく追加してみましょう。

これを実行できるリデューサーが必要です。「operator.add」は、Python の組み込み演算子モジュールの関数です。

`operator.add` をリストに適用すると、リストの連結が実行されます。

ノード 2 と 3 の更新は同じステップにあるため、同時に実行されることがわかります。

ここで、「foo」に「None」を渡すとどうなるかを見てみましょう。

リデューサー `operator.add` が入力として `NoneType` パスを `node_1` のリストに連結しようとするため、エラーが発生します。

## Custom Reducers 

このようなケースに対応するために、[カスタムreducerを定義することもできます](https://langchain-ai.github.io/langgraph/how-tos/subgraph/#custom-reducer-functions-to-manage-state)。

例えば、リストを結合し、入力の片方または両方が`None`の場合を処理するカスタムreducerロジックを定義してみましょう。

「node_1」に値 2 を追加します。

次に、カスタム レデューサーを試してみましょう。エラーがスローされていないことがわかります。

## Messages

モジュール1では、組み込みのreducer `add_messages`を使用して状態内のメッセージを処理する方法を示しました。

また、[メッセージを操作する場合は`MessagesState`が便利なショートカットである](https://langchain-ai.github.io/langgraph/concepts/low_level/#messagesstate)ことも示しました。

* `MessagesState`には組み込みの`messages`キーがあります
* このキーには`add_messages` reducerも組み込まれています

これらは2つは同等です。

簡潔にするため、`from langgraph.graph import MessagesState` 経由で `MessagesState` クラスを使用します。

「add_messages」リデューサーの使用法についてもう少し詳しく説明しましょう。

したがって、`add_messages` を使用すると、状態の `messages` キーにメッセージを追加できることがわかります。

## Re-writing

`add_messages` reducerを使用する際の便利なテクニックをいくつか紹介します。

「メッセージ」リスト内の既存のメッセージと同じ ID を持つメッセージを渡すと、そのメッセージは上書きされます。

## Removal

`add_messages` は [メッセージの削除を有効にする](https://langchain-ai.github.io/langgraph/how-tos/memory/delete-messages/) こともできます。 

このためには、`langchain_core` の [RemoveMessage](https://api.python.langchain.com/en/latest/messages/langchain_core.messages.modifier.RemoveMessage.html) を使用するだけです。

「delete_messages」に示されているように、メッセージ ID 1 と 2 がリデューサーによって削除されていることがわかります。

これが実際に適用されるのはもう少し後になります。
