# Deployment

## Review

メモリを備えたエージェントを構築しました：

* `act` - モデルに特定のツールを呼び出させる 
* `observe` - ツールの出力をモデルに戻す
* `reason` - モデルにツールの出力について推論させ、次に何をするか決定させる(例：別のツールを呼び出すか、直接応答するか)
* `persist state` - インメモリのチェックポインターを使用して、中断を含む長時間の会話をサポート

## Goals

では、実際にエージェントをローカルのStudioおよび`LangGraph Cloud`にデプロイする方法について説明します。

## Concepts 

理解すべき重要な概念がいくつかあります - 

`LangGraph` —
- PythonとJavaScriptのライブラリ
- エージェントワークフローの作成を可能にする

`LangGraph API` —
- グラフコードをバンドル
- 非同期操作を管理するためのタスクキューを提供
- インタラクション間で状態を維持するための永続性を提供

`LangGraph Cloud` --
- LangGraph APIのホステッドサービス
- GitHubリポジトリからのグラフのデプロイを可能にする
- デプロイされたグラフのモニタリングとトレースも提供
- 各デプロイメントに固有のURLでアクセス可能

`LangGraph Studio` --
- LangGraphアプリケーション用の統合開発環境(IDE)
- APIをバックエンドとして使用し、グラフのリアルタイムのテストと探索を可能にする
- ローカルまたはクラウドデプロイメントで実行可能

`LangGraph SDK` --
- LangGraphグラフをプログラムで操作するためのPythonライブラリ
- ローカルでもクラウドでも、グラフを扱うための一貫したインターフェースを提供
- クライアントの作成、アシスタントへのアクセス、スレッド管理、実行の実行を可能にする

## Testing Locally

--

**⚠️ 免責事項**

*Studioの実行には現在Macが必要です。Macを使用していない場合は、このステップをスキップしてください。*

*また、このノートブックをCoLabで実行している場合も、このステップをスキップしてください。*

--

LangGraph Studioでローカルにサービス提供されているグラフに簡単に接続できます！

これはStudio UIの左下隅に表示される`url`を介して行います。

[コードブロックはここでは翻訳を省略]

これで、エージェントを以下のパラメータで[`client.runs.stream`を使って](https://langchain-ai.github.io/langgraph/concepts/low_level/#stream-and-astream)実行できます：

* `thread_id`
* `graph_id`
* `input` 
* `stream_mode`

ストリーミングについては将来のモジュールで詳しく説明します。

今は、`stream_mode="values"`を使ってグラフの各ステップ後の状態の完全な値を[ストリーミング](https://langchain-ai.github.io/langgraph/cloud/how-tos/stream_values/)していることを理解してください。

状態は`chunk.data`に取り込まれます。

## Testing with Cloud

[こちら](https://langchain-ai.github.io/langgraph/cloud/quick_start/#deploy-from-github-with-langgraph-cloud)で説明されているように、LangSmith経由でCloudにデプロイできます。

### GitHubに新しいリポジトリを作成

* GitHubアカウントに移動
* 右上の「+」アイコンをクリックし、`"New repository"`を選択
* リポジトリに名前を付ける(例：`langchain-academy`)

### GitHubリポジトリをリモートとして追加

* このコースの最初に`langchain-academy`をクローンしたターミナルに戻る
* 新しく作成したGitHubリポジトリをリモートとして追加

```
git remote add origin https://github.com/your-username/your-repo-name.git
```
* プッシュする
```
git push -u origin main
```

### LangSmithをGitHubリポジトリに接続

* [LangSmith](https://smith.langchain.com/)に移動
* 左のLangSmithパネルの`deployments`タブをクリック
* `+ New Deployment`を追加
* コース用に作成したGitHubリポジトリ(例：`langchain-academy`)を選択
* `LangGraph API config file`を`studio`ディレクトリのいずれかに指定
* 例えば、モジュール1の場合：`module-1/studio/langgraph.json`を使用
* APIキーを設定(例：`module-1/studio/.env`ファイルからコピー可能)

### デプロイメントを使用する

デプロイメントとは以下のような異なる方法で対話できます：

* 以前と同様に[SDK](https://langchain-ai.github.io/langgraph/cloud/quick_start/#use-with-the-sdk)を使用
* [LangGraph Studio](https://langchain-ai.github.io/langgraph/cloud/quick_start/#interact-with-your-deployment-via-langgraph-studio)を使用

ここでノートブックでSDKを使用するには、単に`LANGSMITH_API_KEY`が設定されていることを確認するだけです！