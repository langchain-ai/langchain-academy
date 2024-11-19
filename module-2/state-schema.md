# State Schema

## Review

モジュール1で基礎を築きました！以下の機能を持つエージェントを構築しました：

* `act` - モデルに特定のツールを呼び出させる 
* `observe` - ツールの出力をモデルに戻す
* `reason` - モデルにツールの出力について推論させ、次に何をするか決定させる(例：別のツールを呼び出すか、直接応答するか)  
* `persist state` - 中断を含む長時間の会話をサポートするためのインメモリチェックポインターを使用

そして、LangGraph Studioでローカルに、またはLangGraph Cloudでデプロイする方法を示しました。

## Goals 

このモジュールでは、状態とメモリの両方についてより深く理解を深めていきます。

まず、状態スキーマを定義するいくつかの異なる方法を見ていきましょう。

## Schema

LangGraph `StateGraph`を定義する際、[状態スキーマ](https://langchain-ai.github.io/langgraph/concepts/low_level/#state)を使用します。

状態スキーマは、グラフが使用するデータの構造と型を表します。

すべてのノードはそのスキーマと通信することが期待されます。

LangGraphは、さまざまなPython [型](https://docs.python.org/3/library/stdtypes.html#type-objects)とバリデーションアプローチに対応する柔軟性を提供します！

## TypedDict

モジュール1で説明したように、Pythonの`typing`モジュールから`TypedDict`クラスを使用できます。

これによりキーとその対応する値の型を指定できます。

ただし、これらは型ヒントであることに注意してください。

[mypy](https://github.com/python/mypy)のような静的型チェッカーやIDEが型関連のエラーをコード実行前に検出するために使用できます。

しかし実行時には強制されません！

より具体的な値の制約には、`Literal`型ヒントなどを使用できます。

ここでは、`mood`は"happy"または"sad"のいずれかのみ取ることができます。

定義された状態クラス(例：ここでの`TypedDictState`)を`StateGraph`に渡すだけで、LangGraphで使用できます。

各状態キーは、グラフの「チャネル」として考えることができます。

モジュール1で説明したように、各ノードで指定されたキーまたは「チャネル」の値を上書きします。

## Dataclass 

[dataclasses](https://docs.python.org/3/library/dataclasses.html)は[構造化データを定義する別の方法](https://www.datacamp.com/tutorial/python-data-classes)を提供します。

データクラスは、主にデータを格納するためのクラスを作成するための簡潔な構文を提供します。

## Pydantic

前述のように、`TypedDict`と`dataclasses`は型ヒントを提供しますが、実行時に型を強制しません。

つまり、エラーを発生させることなく無効な値を割り当てる可能性があります！

例えば、型ヒントで`mood: list[Literal["happy","sad"]]`と指定されているにもかかわらず、`mood`を"mad"に設定できます。

[Pydantic](https://docs.pydantic.dev/latest/api/base_model/)は、Python型アノテーションを使用したデータ検証および設定管理ライブラリです。

検証機能があるため、[LangGraphの状態スキーマを定義するのに特に適しています](https://langchain-ai.github.io/langgraph/how-tos/state-model/)。

Pydanticは、データが実行時に指定された型と制約に準拠しているかどうかを確認する検証を実行できます。

`PydanticState`をグラフでシームレスに使用できます。