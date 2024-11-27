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

[Reducers](https://langchain-ai.github.io/langgraph/concepts/low_level/#reducers)がこの問題に対処する一般的な方法を提供します。

これらは更新の実行方法を指定します。

`Annotated`型を使用してreducer関数を指定できます。

例えば、この場合は各ノードから返された値を上書きするのではなく、リストに追加しましょう。

そのためのreducerが必要です:`operator.add`はPythonの組み込みoperatorモジュールの関数です。

`operator.add`をリストに適用すると、リストの連結が実行されます。

ノード 2 と 3 の更新は同じステップにあるため、同時に実行されることがわかります。

ここで、「foo」に「None」を渡すとどうなるかを見てみましょう。

リデューサー `operator.add` が入力として `NoneType` パスを `node_1` のリストに連結しようとするため、エラーが発生します。

## Custom Reducers 

このようなケースに対応するために、[カスタムreducerを定義することもできます](https://langchain-ai.github.io/langgraph/how-tos/subgraph/#custom-reducer-functions-to-manage-state)。

例えば、リストを結合し、入力の片方または両方が`None`の場合を処理するカスタムreducerロジックを定義してみましょう。

## Messages

モジュール1では、組み込みのreducer `add_messages`を使用して状態内のメッセージを処理する方法を示しました。

また、[メッセージを扱う場合は`MessagesState`が便利なショートカットである](https://langchain-ai.github.io/langgraph/concepts/low_level/#messagesstate)ことも示しました。

* `MessagesState`には組み込みの`messages`キーがあります
* このキーには組み込みの`add_messages` reducerもあります

これらは同等です。

簡潔にするため、`from langgraph.graph import MessagesState`を使用して`MessagesState`クラスを使います。

## Re-writing

`add_messages` reducerを使用する際の便利なテクニックをいくつか紹介します。

既存の`messages`リストに存在するものと同じIDのメッセージを渡すと、上書きされます！

## Removal

`add_messages`は[メッセージの削除も可能](https://langchain-ai.github.io/langgraph/how-tos/memory/delete-messages/)です。

このために、`langchain_core`から[RemoveMessage](https://api.python.langchain.com/en/latest/messages/langchain_core.messages.modifier.RemoveMessage.html)を使用します。

reducerによって`delete_messages`で指定されたメッセージID(1と2)が削除されることがわかります。

これについては後でもっと実践的に見ていきます。
