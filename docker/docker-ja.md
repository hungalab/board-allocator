# Dokcer Support
Dockerを使用してboard-allocatorを仮想環境下で実行することができます。

## Usage
基本的な操作はmakefileに書かれている通りです。
### make build
- docker imageをbuildします。
### make start
- 上で作ったdocker imageを実行します。
- このディレクトリから見て親ディレクトリ以下を仮想環境下にマウントします
- ローカルPC(Dockerコンテナが動いているPC)のユーザidとグループidを持つユーザを作成します (i.e. コンテナ内で追加/編集されたファイルの所有者はローカルのPCで操作したときと同じになります)
### make runwdisp
- X転送を有効化します。
- それ以外は"make start"をした時と同じになります。