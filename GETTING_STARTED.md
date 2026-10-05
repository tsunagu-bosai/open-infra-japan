# はじめて使う人へ

このページは、GitやPythonを使ったことがない人も対象にしています。

「Pythonは入っているのか？」「どの画面にコマンドを入力するのか？」というところから説明します。

このリポジトリのデータを見るだけなら、Pythonは必要ありません。

ツールを実行したい場合だけ、以下の環境構築を行ってください。

---

# まず、自分のOSを確認する

使っているパソコンによって、最初に開く画面が違います。

| パソコン                    | この手順書で使う環境       |
| ----------------------- | ---------------- |
| Windows 10 / 11         | WSL2 + Ubuntu    |
| Linux                   | Terminal / bash  |
| macOS                   | Terminal         |
| Windows PowerShellだけで実行 | この手順書では基本的に扱いません |

WindowsではPowerShellから直接Pythonを動かすこともできますが、Linuxとはコマンドが異なります。

このプロジェクトではLinux系のコマンドを多く使用するため、Windowsユーザーには **WSL2 + Ubuntu** を推奨します。

以降のコマンド例は、特に記載がない限り **Ubuntu / Linux / macOSのターミナル** に入力します。

---

# Windowsを使っている場合

## 1. PowerShellを管理者として開く

Windowsのスタートメニューで

`PowerShell`

と検索します。

「Windows PowerShell」または「ターミナル」を右クリックして、

「管理者として実行」

を選択します。

## 2. WSLとUbuntuをインストールする

PowerShellに次を入力します。

```
wsl --install -d Ubuntu
```

インストールが終わったら、Windowsを再起動します。

## 3. Ubuntuを起動する

Windowsのスタートメニューから

`Ubuntu`

を起動します。

初回起動時にLinux用のユーザー名とパスワードを聞かれます。

Windowsのユーザー名・パスワードと同じである必要はありません。

パスワードを入力しても画面には文字が表示されません。これは正常です。

以降、この手順書のコマンドは **PowerShellではなくUbuntuの画面** に入力します。

---

# Linuxを使っている場合

UbuntuやDebian系Linuxでは「Terminal」を起動してください。

以降のコマンドをそのまま実行できます。

---

# macOSを使っている場合

「ターミナル」を起動してください。

Finderから

```
アプリケーション
→ ユーティリティ
→ ターミナル
```

で開けます。

macOSでは標準シェルが `zsh` ですが、この手順書で使用する基本的なコマンドはほぼ同じです。

---

# GitとPythonを準備する

## Windows + WSL / Ubuntu / Debian

Ubuntuの画面で次を実行します。

```
sudo apt update
```

次に、

```
sudo apt install -y git python3 python3-venv python3-pip
```

を実行します。

途中でパスワードを聞かれた場合は、Ubuntu作成時のパスワードを入力します。

---

# インストールできたか確認する

次を実行します。

```
git --version
```

続けて、

```
python3 --version
```

例えば、

```
git version 2.x.x
Python 3.x.x
```

のように表示されれば準備完了です。

`command not found` と表示された場合は、GitまたはPythonがまだインストールされていません。

---

# `python` と `python3` は何が違うのか

Linuxでは通常、

```
python3
```

がPython 3を意味します。

一方、このプロジェクトでは仮想環境を有効にした後は、

```
python
```

を使用します。

つまり、この手順書では次のルールに統一します。

```
仮想環境を作る前
    python3

仮想環境を有効にした後
    python
```

混在しているように見えますが、意味があります。

---

# リポジトリを取得する

GitHubのこのリポジトリのページを開きます。

「Code」ボタンを押し、

「HTTPS」

を選択してURLをコピーします。

Ubuntu / Terminalで、作業用ディレクトリを作ります。

```
mkdir -p ~/project
```

移動します。

```
cd ~/project
```

GitHubからコピーしたURLを使って、

```
git clone コピーしたURL
```

を実行します。

例:

```
git clone https://github.com/xxxxx/open-infra-japan.git
```

取得できたら、

```
cd open-infra-japan
```

を実行します。

現在いる場所を確認したい場合は、

```
pwd
```

ファイル一覧を確認したい場合は、

```
ls
```

を使います。

`README.md`、`catalog`、`data`、`tools` などが表示されれば、正しい場所にいます。

---

# Windows + WSLを使う場合の注意

プロジェクトはできれば、

```
~/project/open-infra-japan
```

のようにWSL側へ置いてください。

初心者の場合、

```
/mnt/c/...
```

配下のWindowsフォルダへ置く必要はありません。

WSLのLinux側へ置いた方が、ファイル権限や実行環境の違いによる問題を減らせます。

---

# データを見るだけの場合

ここまでで十分です。

Python環境を作る必要はありません。

正規化済みのデータは、

```
data/normalized/
```

にあります。

例えば、

```
data/normalized/
  06-山形県/
    06210-天童市/
      public-toilet/
        public-toilet.csv
```

という構成です。

`public-toilet.csv` が実際に利用する正規化済みデータです。

---

# データの出典を確認する

次のファイルを確認します。

```
catalog/datasets.csv
```

ここには、

```
自治体名
元データセット名
公開元ページ
ダウンロードURL
ファイル形式
ライセンス
最終確認日
```

などが記録されています。

---

# 全国の調査状況を見る

次のファイルを確認します。

```
catalog/public_toilet_municipality_status.csv
```

主なstatusは次の意味です。

| status               | 意味                                   |
| -------------------- | ------------------------------------ |
| `cataloged`          | 対象データセットを確認してcatalog登録済み             |
| `searched-not-found` | 公式サイト等を調査したが対象のCSV/XLS/XLSXを確認できなかった |
| `candidate`          | 候補が残っており追加確認が必要                      |
| `not-searched`       | 自治体単位の直接調査が未実施                       |

全国調査の現在地を確認するときは、このファイルを基準にします。

candidateやreviewという名前のCSVには、過去の探索途中のデータも含まれます。

---

# Pythonツールを実行したい場合

ここから先は、データを見るだけの人には不要です。

## 1. 仮想環境を作る

リポジトリのトップディレクトリで、

```
python3 -m venv .venv
```

を実行します。

`.venv` は、このプロジェクト専用のPython環境です。

パソコン全体のPython環境を汚さずに必要なライブラリをインストールできます。

作成するのは最初の1回だけです。

## 2. 仮想環境を有効にする

Ubuntu / Linux / macOSでは、

```
source .venv/bin/activate
```

を実行します。

成功すると、ターミナルの先頭に、

```
(.venv)
```

のような表示が出ることがあります。

## 3. 必要なPythonライブラリをインストールする

```
python -m pip install --upgrade pip
```

続けて、

```
python -m pip install -r requirements.txt
```

を実行します。

これも通常は最初の1回だけです。

---

# 次回からは何をすればいいのか

パソコンを再起動した後などは、仮想環境が解除されています。

毎回次の2つを行います。

まずリポジトリへ移動します。

```
cd ~/project/open-infra-japan
```

次に仮想環境を有効化します。

```
source .venv/bin/activate
```

これで、

```
python ...
```

というコマンドを実行できる状態になります。

---

# 動作確認をする

まず全国自治体の調査statusを生成してみます。

```
python tools/catalog/build_public_toilet_municipality_status.py
```

エラーが出ず、

```
cataloged:
searched-not-found:
not-searched:
```

などの集計が表示されれば動作しています。

生成されるファイルは、

```
catalog/public_toilet_municipality_status.csv
```

です。

---

# 正規化済みデータを検査する

全国分を検査する場合は、

```
python tools/validate_public_toilet.py --input normalized
```

を実行します。

かなり長い結果が表示されます。

特定の都道府県だけ検査することもできます。

山形県の場合:

```
python tools/validate_public_toilet.py --prefecture 06 --input normalized
```

出力が長い場合は、

```
python tools/validate_public_toilet.py --prefecture 06 --input normalized > /tmp/validate_yamagata.txt
```

としてファイルへ保存できます。

表示する場合は、

```
less /tmp/validate_yamagata.txt
```

を実行します。

`less` を終了するときは、

```
q
```

キーを押します。

---

# ERROR / WARNING / INFO の意味

`ERROR`

データとして扱う前に確認すべき問題です。

例:

```
自治体コードの形式エラー
自治体コードの不一致
数値列の不正値
```

`WARNING`

自動修正せず確認対象として残しているものです。

例:

```
IDの重複
時刻表記の違い
緯度経度の不自然な値
```

公式元データに同じIDが存在しても、正規化処理で勝手に別IDへ書き換えません。

`INFO`

欠損等のデータ品質情報です。

例:

```
ID空欄
緯度空欄
経度空欄
```

INFOが存在するだけで、そのデータセットが利用不能という意味ではありません。

---

# raw と normalized の違い

```
data/raw/
```

は公開元から取得した元データを作業環境で保存する場所です。

元データそのものは、再配布条件・容量・更新履歴の肥大化等を考慮し、
この公開リポジトリには含めていません。

正規化処理を再実行する場合は、公開元から取得した元データを
別途 `data/raw/` に配置する必要があります。

```
data/normalized/
```

は、元データを共通形式へ整理したデータです。

アプリや分析で利用する場合はこちらを使用します。

元データに存在しない値を、推測だけで埋めることは原則として行いません。

---

# 元データから正規化し直す

データ源ごとの変換処理は、

```
tools/normalize/
```

にあります。

都道府県ごとの正規化入口は、

```
tools/normalize/prefectures/
```

にあります。

例えば山口県は、

```
python3 tools/normalize/prefectures/p35_yamaguchi.py
```

で実行できます。

地方単位・全国一括の入口も用意しています。

全国:

```
python3 tools/normalize/all_japan.py
```

ただし、正規化には公開元から取得した `data/raw/` が必要です。
この公開リポジトリには元データそのものを含めていないため、
clone直後の状態だけで全国を再生成することはできません。

実行後はvalidatorで確認します。

```
python3 tools/validate_public_toilet.py --prefecture 35 --input normalized
```

---

# cloneしただけで全国データをゼロから再構築できるのか

できません。

このプロジェクトには、

```
公式サイトの調査
データセットの選定
CSV / XLS / XLSX の取得
schema確認
ライセンス確認
非標準データの変換
人手による内容確認
```

が含まれています。

したがって、

```
git clone
    ↓
コマンド1個
    ↓
全国データ完全再構築
```

という構成ではありません。

確認済み成果物はリポジトリへ保存し、再現可能な処理は `tools/` に残しています。

---

# `searched-not-found` は「公衆トイレがない」という意味ではない

重要です。

`searched-not-found` は、

「その自治体に公衆トイレが存在しない」

という意味ではありません。

調査時点で、このプロジェクトの収集対象としている構造化データ、

```
CSV
XLS
XLSX
```

を公式サイト等から確認できなかった、という意味です。

PDFやHTMLには情報が存在する場合があります。

---

# Windows PowerShellで直接実行したい場合

Python自体はWindows PowerShellからも利用できます。

ただし、

```
仮想環境の有効化方法
パス表記
複数行コマンド
shellコマンド
```

などがLinuxと異なります。

そのため、初心者向けの標準手順ではWSL2 + Ubuntuを使用します。

PowerShellネイティブでの実行は、WindowsとPythonの環境構築を理解している人向けとします。

---

# 困ったときに確認するもの

「今どこのディレクトリにいる？」

```
pwd
```

「ファイルは何がある？」

```
ls
```

「Python環境は有効？」

```
which python
```

`.venv/bin/python` のように表示されれば仮想環境が有効です。

「Pythonのバージョンは？」

```
python --version
```

「Gitは使える？」

```
git --version
```

「仮想環境を終了したい」

```
deactivate
```

---

# 最初に覚えるのはこの4つだけ

データを使う:

```
data/normalized/
```

出典を見る:

```
catalog/datasets.csv
```

全国進捗を見る:

```
catalog/public_toilet_municipality_status.csv
```

データを検査する:

```
python tools/validate_public_toilet.py --input normalized
```

分からなくなったら、まずこのページの上から順番に確認してください。
