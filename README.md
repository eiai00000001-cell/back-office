# 個人事業(EIAI TEC)向け事務管理システム

## 1. 文書情報

- 作成日: 2026-09-16 / 改訂日: 2026-09-17
- 版数: 2.0(イテレーション2: 財務ダッシュボード追加)
- 参照元:
  - `docs/02_architect/詳細設計書.md`(版数2.0)
  - `docs/02_architect/基本設計書.md`(版数2.0)
  - `docs/02_architect/mockups/`(SC-01〜SC-12)
  - `docs/01_requirements/機能仕様書.md`・`要件定義書.md`
  - `docs/03_develop/レビュー結果報告書.md`(版数1.0、イテレーション1分)
- 対応イテレーション: イテレーション1(初回実装、レビュー指摘対応を含む)、イテレーション2(財務ダッシュボード F-07 / SC-12 追加)

---

## 2. 実装概要

### 2.1 採用技術(基本設計書2.1章のとおり)

| 分類 | 技術 |
|---|---|
| バックエンド | Python 3.13(※1)+ FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 + Uvicorn |
| PDF生成 | WeasyPrint + Jinja2 |
| DB | SQLite 3(`db/back_office.db`) |
| フロントエンド | React 18 + TypeScript + Vite + MUI v5 |
| グラフ描画 | Recharts(v3、財務ダッシュボードSC-12、イテレーション2で追加) |
| API通信/状態管理 | TanStack Query + Axios |
| ルーティング | React Router v6 |
| フォーム | React Hook Form + Zod(取引先マスタ・システム設定画面) |
| テスト | pytest(backend)/ Vitest + Testing Library(frontend) |

(※1)詳細設計書はPython 3.12を指定しているが、開発環境にPython 3.12が存在しなかったため、pyenvで利用可能なPython 3.13.3を使用した。3.12系との言語仕様差異は軽微であり、動作確認上の問題は確認していない。「6. 詳細設計書との差異」に記載。

### 2.2 ディレクトリ構成

```
back-office/
  backend/                 … FastAPIアプリケーション
    app/
      models/               … SQLAlchemy宣言的モデル(8テーブル)
      schemas/               … Pydanticスキーマ(リクエスト/レスポンス)
      repositories/           … DBアクセス層
      services/                … 業務ロジック層(税計算・採番・入金判定・変換・財務ダッシュボード集計等)
      routers/                  … APIルーター(FastAPI APIRouter。`dashboard.py`はイテレーション2で追加)
      utils/                     … 共通ユーティリティ(`date_range.py`: 直近12ヶ月算出、イテレーション2で追加)
      templates/                 … PDF生成用Jinja2テンプレート
      dependencies.py             … DI(ルーター→サービス→リポジトリの組み立て)
      config.py                    … パス設定(db/・data/の場所解決)
      database.py                   … SQLAlchemy Engine/Session
      main.py                        … アプリ起動・例外ハンドラ・静的配信
    alembic/                  … DBマイグレーション(初回スキーマ+company_profile初期データ投入、イテレーション2で財務ダッシュボード向けインデックス追加リビジョンを追加)
    scripts/                  … launch.sh / stop.sh(起動.app・終了.app から呼び出し)
    tests/                    … pytest(単体・APIレベル結合テスト)
    static/                   … npm run build の生成物の配置先(gitignore対象)
    data/attachments/          … (未使用。実際の添付ファイルは3.3節参照)
  frontend/                 … React + TypeScript(Vite)
    src/
      api/                    … Axiosベースのバックエンド呼び出し(`__tests__/`にVitestテスト。`dashboard.ts`はイテレーション2で追加)
      pages/                   … SC-01〜SC-12に対応する12画面(`__tests__/`にVitest+Testing Libraryのコンポーネントテスト。`DashboardPage.tsx`はイテレーション2で追加)
      components/               … 共通コンポーネント(ヘッダー・品目明細エディタ)
      utils/                      … 税計算(サーバー側ロジックのミラー)・表示フォーマット(`__tests__/`にVitestテスト)
      types/                       … 型定義・列挙値・日本語ラベル
  db/                       … SQLiteファイル配置先(`back_office.db`、gitignore対象)
  data/attachments/expenses/ … 領収書添付ファイル配置先(gitignore対象、3.3節参照)
  scripts/build_apps.sh     … 起動.app・終了.app 生成スクリプト
  dist/                     … 起動.app・終了.app 生成物(gitignore対象)
  docs/                     … 計画・要件定義・設計フェーズの成果物(参照のみ)
```

---

## 3. セットアップ手順

以下はいずれも実際に実行し、動作を確認済みのコマンドである。

### 3.1 バックエンド

```bash
cd back-office
brew install pango gdk-pixbuf libffi cairo   # WeasyPrintの実行時依存ライブラリ
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cd backend
../backend/.venv/bin/alembic upgrade head     # db/back_office.db にスキーマを作成(イテレーション2で財務ダッシュボード向けインデックスのリビジョンを追加、適用済みであることを確認済み)
```

### 3.2 フロントエンド(開発時)

```bash
cd frontend
npm install             # イテレーション2でRecharts(グラフ描画ライブラリ)を追加
npm run dev            # http://localhost:5173 (APIは/apiがlocalhost:8000へプロキシされる)
```

開発時は別ターミナルでバックエンドも起動しておくこと。

```bash
cd backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3.3 本番相当の起動確認(実運用構成)

```bash
cd frontend && npm run build          # backend/static に生成物を出力
cd ../backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`http://127.0.0.1:8000/` にアクセスし、React SPAとAPIが単一プロセス・単一ポートで動作することを確認済み(ホーム→請求書一覧→見積書作成→請求書変換→入金登録→PDF出力までの一連の操作をcurl/ブラウザ双方で確認)。

### 3.4 起動.app / 終了.app(詳細設計書4.7章)

```bash
bash scripts/build_apps.sh   # dist/起動.app, dist/終了.app を生成
```

`backend/scripts/launch.sh`・`stop.sh`は単体で実行して動作確認済み(ヘルスチェック→Uvicornバックグラウンド起動→ブラウザオープン、SIGTERM停止→PIDファイル削除→osascript通知)。`起動.app`/`終了.app`自体のダブルクリック起動は、GUI操作を伴うためこの開発環境(エージェント実行環境)では確認できていない。EIAI TEC本人の実機での最終確認を推奨する(「7. 要確認事項」参照)。

### 3.5 テスト実行

```bash
cd backend && .venv/bin/python -m pytest -q
cd frontend && npx vitest run
```

---

## 4. 実装状況

| 機能ID | 機能名 | 状態 | 補足 |
|---|---|---|---|
| F-01 | 請求書発行 | 実装済み | SC-02/SC-03、`InvoiceService`・`TaxCalculationService`・`NumberingService`・PDF生成 |
| F-02 | 経費管理 | 実装済み | SC-06/SC-07/SC-08、`ExpenseService`・`AttachmentService`(添付ファイル検証・保存・取得) |
| F-03 | 見積書作成 | 実装済み | SC-04/SC-05、`QuoteService`(F-01と税計算・採番ロジックを共有) |
| F-04 | 見積→請求の自動変換 | 実装済み | `QuoteToInvoiceConversionService`。1対1制約はDBのUNIQUE制約+事前チェックの二重化 |
| F-05 | 入金・売掛金管理 | 実装済み | SC-03入金記録セクション、SC-09売掛金一覧、`PaymentService`(ステータス・期限超過算出) |
| F-06 | ホーム画面・共通UI | 実装済み | SC-01、`HomeSummaryService`。サマリー取得失敗時のエラー表示分離も実装 |
| (共通) | 取引先マスタ管理 | 実装済み | SC-10、`ClientService` |
| (共通) | システム設定(発行者情報) | 実装済み | SC-11、`CompanyProfileService`(id=1固定シングルトン) |
| (共通) | アプリ起動・終了(.app化) | 実装済み | `scripts/launch.sh`・`stop.sh`・`build_apps.sh`(3.4節参照、実機でのダブルクリック確認は未実施) |
| F-07 | 財務ダッシュボード(イテレーション2) | 実装済み | SC-12、`DashboardService`(読み取り専用)。4区画(売上・入金状況/経費/損益/見積状況)に対応する4本のAPIを独立実装し、区画ごとにフロントエンドでエラー表示を分離(4.8.6章)。直近12ヶ月の月次集計(発生主義)・0円/0件補完・見積成約率の0除算回避を実装。ホーム画面(SC-01)に導線カードを追加 |

全12画面(SC-01〜SC-12)・全29 APIエンドポイント(+ヘルスチェック+財務ダッシュボード4本の合計34本)を実装済み。詳細設計書7章のAPI設計との対応は1:1。

---

## 5. テスト実行結果

### 5.1 バックエンド(pytest)

- 実行コマンド: `backend/.venv/bin/python -m pytest -q`
- 結果: **149 passed**(TDDによる単体テスト+APIレベル結合テスト、失敗0件。イテレーション1の127件+イテレーション2で追加した22件)
- 内訳(主なテスト対象): `TaxCalculationService`・`NumberingService`・`PaymentService`(入金ステータス・期限超過判定・入金登録)・`InvoiceService`・`QuoteService`・`QuoteToInvoiceConversionService`(1対1制約・独立性)・`ExpenseService`(期間From/Toバリデーションを含む)・`AttachmentService`(拡張子・サイズ検証、パストラバーサル拒否、添付ファイル削除)・`HomeSummaryService`・`PdfGenerationService`(WeasyPrint実PDF生成)・`ClientService`・`CompanyProfileService`、`main.py`の例外ハンドラ(バリデーションエラーの日本語メッセージ整形・予期しない例外のログ記録)、および全ルーターのAPI結合テスト(clients/company-profile/invoices/quotes/expenses/payments/home/health/dashboard)
- イテレーション2追加分: `build_last_12_months`/`month_start`/`month_end`(`tests/test_date_range.py`、年またぎ・うるう年を含む7件)、`DashboardService`(`tests/test_dashboard_service.py`、月次売上・入金額・経費・損益・見積件数金額の集計、issue_date NULLの除外、月次0円/0件補完、見積成約率の算出・0除算回避の10件)、財務ダッシュボードAPI(`tests/test_api_dashboard.py`、4エンドポイントの疎通・実データ反映の5件)

### 5.2 フロントエンド(Vitest)

- 実行コマンド: `frontend && npx vitest run`
- 結果: **37 passed**(失敗0件。イテレーション1の30件+イテレーション2で追加した7件)
- 内訳: `calculateTotals`/`calculateItemAmount`(サーバー側`TaxCalculationService`と同一ロジックのフロントエンド版、詳細設計書4.1ステップ6のリアルタイム表示要件に対応)、`formatCurrency`/`isOverdueDate`(表示フォーマット共通処理)、`extractErrorMessage`(配列形式detailへの防御的処理)、`InvoiceDetailPage`(保存・入金登録・超過確認ダイアログ・取引先「新規登録」リンク遷移・`selectedClientId`復帰のコンポーネントテスト)、`QuoteDetailPage`(取引先「新規登録」リンク遷移・`selectedClientId`復帰のコンポーネントテスト)、`ExpenseFormPage`(添付ファイル検証・保存ボタン活性制御のコンポーネントテスト)
- イテレーション2追加分: `formatMonthLabel`/`formatLast12MonthsRangeLabel`(`src/utils/__tests__/format.test.ts`、4件)、`DashboardPage`(`src/pages/__tests__/DashboardPage.test.tsx`、全区画正常表示・区画単位のエラー分離表示・見積成約率0除算時の「-」表示の3件)

### 5.3 TypeScriptビルド・ESLint相当

- `npx tsc -b`: エラーなし(Recharts v3のTooltip formatter/labelFormatter型に合わせて型安全なラッパー関数を用意)
- `npm run build`: 成功(`backend/static`に生成物出力を確認)

---

## 6. 詳細設計書との差異

| # | 項目 | 詳細設計書の記載 | 実装内容 | 理由 |
|---|---|---|---|---|
| 1 | Pythonバージョン | 3.12 | 3.13.3(pyenv) | 開発環境にPython 3.12がインストールされておらず、3.11(Homebrew)より新しい3.13を採用。FastAPI/SQLAlchemy/WeasyPrint等、使用ライブラリはいずれも3.13対応済みで、動作確認上の問題は発生していない。EIAI TEC本人の実機セットアップ時にPython 3.12が利用可能であれば、`backend/.venv`を3.12で作成し直すことで詳細設計書の記載どおりに戻せる(コード変更は不要)。 |
| 2 | 添付ファイル保存先パス(4.2章) | `backend/data/attachments/expenses/{expense_id}/...` | プロジェクトルート直下の`data/attachments/expenses/{expense_id}/...`(`backend/`配下ではない) | 詳細設計書2章・基本設計書3章・7章は「データ保存場所はプロジェクトフォルダ配下の`db/`・`data/`」と明記しており、基本設計書のシステム構成図でも`db`・`Files`(添付・PDF)はバックエンドプロセスと並列のノードとして描かれている。4.2章の具体パス記載とこの全体方針との間に軽微な不整合があったため、後者(基本設計書のシステム構成方針)を優先し、プロジェクトルート直下の`data/`配下に統一した。DBファイルも同様に`db/back_office.db`とし、`backend/app/config.py`で絶対パス解決している(cwdに依存しない)。 |
| 3 | データベースマイグレーション | Alembicでスキーマ変更履歴を管理(基本設計書2.1章) | Alembicの初期マイグレーション(`backend/alembic/versions/`)を作成し、`company_profile`への初期データ投入(詳細設計書6.3章)もマイグレーション内で実施。加えて`main.py`起動時に`Base.metadata.create_all()`を安全網として実行(冪等) | 単一ユーザーの個人利用アプリという性質上、開発時の取り回しやすさを優先し、Alembicの初回マイグレーション整備と並行してcreate_all()による自動テーブル作成も残した。今後のスキーマ変更は新規Alembicリビジョンとして追加する運用を想定。 |
| 4 | フロントエンドのフォーム実装 | 明記なし(React Hook Form + Zodを採用技術として選定、基本設計書2.1章) | 取引先マスタ・システム設定画面はReact Hook Form + Zodで実装。請求書・見積書・経費の画面は、品目明細の動的な行追加・削除を伴う複雑なフォームのため、Reactの`useState`による素朴な状態管理で実装 | RHFのフィールド配列(useFieldArray)を用いた実装も可能だが、開発規模とのバランスを考慮し、複雑な動的配列フォームは素朴な状態管理を採用した。挙動・バリデーション内容は詳細設計書3章の入力項目定義表に準拠している。 |
| 5 | SC-09売掛金一覧の「入金済み金額」列 | API設計(7章)の`InvoiceListItemResponse`に入金済み金額は明記なし | `InvoiceListItemResponse`に`paid_amount`(入金済み金額の合計)を追加 | 基本設計書4.10章の画面レイアウトおよびmockup(SC-09)に「入金済み金額」列が明記されているため、API設計を実装レベルで補完した。仕様の追加ではなく、既存の確定仕様(mockup)をAPIに反映したものである。 |
| 6 | SC-12損益(収支)区画の凡例文言(イテレーション2) | mockup(`SC-12_financial-dashboard.html`)は赤字月の凡例に「例: 26/1」というダミーデータ固有の月を含む | 「赤字月(売上-経費 < 0円)」とし、ダミーデータに紐づく具体的な月の例示は含めない | mockupの当該箇所はダミーデータ(2025年10月〜2026年9月の架空の集計値)に基づく例示であり、実データでは同じ月が赤字になるとは限らないため、実装では一般化した文言とした。基本設計書4.13章の要求(黒字・赤字を視覚的に区別する配色)自体は満たしている。 |
| 7 | SC-12各区画の読み込み中表示(イテレーション2) | mockupは読み込み完了後の表示例とエラー時表示例(コメントアウト)のみを示し、読み込み中の状態については明記なし | 各区画のデータ取得中は「読み込み中です…」という簡易な状態表示を追加 | 4区画が独立してAPIを呼び出す構成(4.8.6章)のため、取得完了までの間、区画ごとに空白のカードが表示され続けることを避ける目的で、最小限の状態表示を追加した。新しい装飾やレイアウトの追加ではなく、既存のエラー表示(「情報を取得できませんでした」)と対になる一時的な文言に留めている。 |

### 6.1 運用ルール: Alembicと`create_all()`の併用について

`main.py`の`Base.metadata.create_all(bind=engine)`は「存在しないテーブルを作成する」だけであり、既存テーブルへのカラム追加・型変更等は一切反映しない。そのため、**今後のイテレーションでSQLAlchemyモデルに変更(カラム追加・型変更・制約変更等)を加える場合は、必ず対応するAlembicリビジョンを`backend/alembic/versions/`に追加すること**を運用ルールとして明文化する(レビュー結果報告書 指摘5対応)。`create_all()`はあくまで初回セットアップ時の安全網であり、スキーマ変更の管理主体はAlembicとする。リビジョン追加を怠ると、アプリのコードが期待するスキーマと実際のDBスキーマが起動時エラーにならずに静かに乖離し、該当カラムへのアクセス時点で初めて例外になるおそれがある。

---

## 7. 要確認事項・未解決事項

| ★ | 内容 | 影響 | 確認方法 | 確認先 | 期限目安 |
|---|---|---|---|---|---|
| 1 | Python 3.12ではなく3.13.3で開発・動作確認した(差異1参照) | 低(動作確認上の問題なし) | EIAI TEC本人の実機にPython 3.12が導入可能か確認 | EIAI TEC本人 | 納品(deployer)フェーズまで |
| 2 | `起動.app`/`終了.app`のダブルクリック起動そのものは、GUI操作を伴うため本開発環境では実機確認できていない(`launch.sh`/`stop.sh`単体の動作は確認済み) | 中(日常利用の起点となる機能) | EIAI TEC本人の実機で`dist/起動.app`・`dist/終了.app`をダブルクリックし、ブラウザが自動的に開くこと・終了通知が出ることを確認 | EIAI TEC本人/tester | テストフェーズ |
| 3 | `frontend`の`npm audit`で、Vite/esbuild(開発サーバー限定の脆弱性)およびReact Router(Open Redirect関連)に中〜高リスクの指摘がある(いずれも`npm audit fix --force`でメジャーバージョンアップが必要) | 低(ローカル・単一ユーザー・127.0.0.1限定運用のため実害は限定的と判断) | `npm audit`の内容を確認し、必要に応じて次イテレーションでメジャーバージョンアップを検討 | reviewer/次イテレーション | 次回イテレーション |
| 4 | フロントエンドのバンドルサイズが約645KB(gzip後202KB)で、Viteのデフォルト警告閾値(500KB)を超過している | 低(単一ユーザー・ローカル利用のため体感上の影響は軽微) | 将来的にコード分割(dynamic import)等を検討 | 次回イテレーション | 任意 |
| 5 | `db/`配下に開発中のスモークテストで作成したSQLiteバックアップファイル(`back_office.db.*-backup`)が複数残っている(いずれも`.gitignore`対象で追跡外) | 低 | 不要であれば削除してよいか、EIAI TEC本人またはreviewerの判断を仰ぐ(developerからは削除不可のルールのため残置) | reviewer | レビューフェーズ |
| 6 | (イテレーション2)財務ダッシュボードAPI実装後の動作確認時、実データベース(`db/back_office.db`)に対して一時的な確認用取引先(「ダッシュボード確認用取引先」)を1件作成した。関連する請求書・見積書等は作成しておらず、確認後に当該取引先1件のみを削除し、確認前の状態(全テーブル0件)に復元済みであることをSQLiteで確認済み | 低(復元済みだが、実データベースへの一時的な書き込みを伴った操作である旨を明示) | `db/back_office.db`の`clients`テーブル等が意図した内容であることをEIAI TEC本人が必要に応じて確認 | EIAI TEC本人 | 任意(復元確認済みのため必須ではない) |

基本設計書8章・詳細設計書9章に記載の要確認事項はすべて確定済みであり、本書時点で持ち越しとなる新規の未解決事項はない(上記は本実装フェーズで新たに生じたもの)。

---

## 8. 変更履歴

| 版数 | 日付 | 内容 | 対応イテレーション |
|---|---|---|---|
| 1.0 | 2026-09-16 | 初版作成。詳細設計書1.1・基本設計書1.2・mockups(SC-01〜SC-11)をもとに、バックエンド(FastAPI、4層構成、8テーブル、29+1 APIエンドポイント、TDDによるpytestテスト108件)・フロントエンド(React 18 + TS + Vite + MUI、全11画面、Vitestテスト13件)・起動/終了.appのビルド一式を実装。 | イテレーション1(初回) |
| 1.1 | 2026-09-16 | `docs/03_develop/レビュー結果報告書.md`(版数1.0)の指摘のうちコード修正で対応可能な11件(高2件・中4件・低5件)に対応。主な内容: (1)バリデーションエラー時の422応答を単一の日本語文字列`detail`に整形する`RequestValidationError`ハンドラを追加し、`InvoiceItemInput`等の主要スキーマにField(description=...)の代替となる`field_validator`を追加、フロントエンド`extractErrorMessage()`に配列形式detailへの防御的処理を追加、`ItemsEditor`利用画面(請求書/見積書)に保存前チェック・保存ボタン活性制御を追加。(2)経費領収書アップロードのパストラバーサル対策(`AttachmentService`にファイル名検証を追加)。(3)予期しない例外を`logging.exception`でUvicornエラーログへ記録。(4)経費一覧の期間(From/To)バリデーションをフロント・バックエンド双方に追加。(5)Alembic運用ルールを本書6.1節に明文化。(6)`InvoiceDetailPage`・`ExpenseFormPage`にTesting Libraryによるコンポーネントテストを追加。(8)`InvoiceRepository.exists_by_source_quote_id`に設計書対応関係のコメントを追加。(9)`ItemsEditor`の行`key`を`crypto.randomUUID()`ベースの安定IDに変更。(10)経費削除時に添付ファイル実体も削除する処理を追加。(11)`ClientMasterPage`の呼び出し元復帰遷移を`useNavigate()`によるクライアントサイド遷移に置き換え。バックエンド127件・フロントエンド26件のテストが全件成功することを確認済み。指摘7(`backend/data/attachments/.gitkeep`削除)・指摘12(詳細設計書パス記載更新)は対象外(前者はファイル削除のためユーザー許可待ち、後者はarchitectフェーズ対応)。 | イテレーション1(レビュー指摘対応) |
| 1.2 | 2026-09-16 | `docs/04_test/テスト結果報告書.md`(版数1.0)で不合格となったTC-C06(重大度: 高、取引先マスタ画面SC-10への遷移導線欠落)に対応。詳細設計書3.3章・3.5章およびmockup(SC-03/SC-05)のとおり、`InvoiceDetailPage.tsx`・`QuoteDetailPage.tsx`の取引先選択欄(`Autocomplete`)の隣に「新規登録」インラインリンク(`/clients?returnTo=<現在のパス>`へ遷移)を追加し、`ClientMasterPage.tsx`側の既存の呼び出し元復帰ロジック(`?selectedClientId=<id>`付きでの復帰)に対応する形で、両画面に`selectedClientId`クエリパラメータ受け取り時の取引先選択状態復元処理を追加した。TDD方針に基づき、先にコンポーネントテスト(`InvoiceDetailPage.test.tsx`へのテスト追加2件、新規`QuoteDetailPage.test.tsx`2件)をRed状態で作成してから実装し、Green化を確認した。バックエンド127件(影響なし・変更なし)・フロントエンド30件(既存26件+新規4件)のテストが全件成功。単一機能に閉じたフロントエンドの結線修正のため、設計整合性への影響はなく、reviewerへの再レビュー依頼は不要と判断し、testerの実機再確認に委ねる。 | イテレーション1(テスト指摘対応) |
| 2.0 | 2026-09-17 | イテレーション2: 財務ダッシュボード(F-07、SC-12)を新規実装。詳細設計書2.0・基本設計書2.0・mockup(`SC-12_financial-dashboard.html`)をもとに、TDD方針(Red→Green→Refactor)で以下を実装。バックエンド: 直近12ヶ月算出の共通ユーティリティ`app/utils/date_range.py`(`build_last_12_months`/`month_start`/`month_end`)、`InvoiceRepository.aggregate_total_by_issue_month`・`PaymentRepository.aggregate_amount_by_payment_month`・`QuoteRepository.aggregate_count_and_amount_by_issue_month`/`count_in_period`/`count_converted_in_period`(既存`ExpenseRepository.aggregate_by_month`/`aggregate_by_category`はF-02と共用・無変更で再利用)、読み取り専用の`DashboardService`(発生主義での月次集計、issue_date NULLの除外、0円/0件補完、見積成約率の0除算回避)、`routers/dashboard.py`(区画ごとに独立した4本のGETエンドポイント)、レスポンススキーマ`app/schemas/dashboard.py`。既存の`Invoice.issue_date`・`Quote.issue_date`・`Payment.payment_date`にインデックスを追加し(詳細設計書6.4章)、Alembicリビジョン`2e1e85c3b7cc`を追加・適用。フロントエンド: `DashboardPage.tsx`(Recharts v3を用いた4区画のグラフ描画、区画単位で独立したTanStack Queryフックによるエラー分離表示)、`api/dashboard.ts`、`utils/format.ts`に`formatMonthLabel`/`formatLast12MonthsRangeLabel`を追加、ホーム画面(SC-01)に「財務ダッシュボード」導線カードを追加、ルーティングに`/dashboard`を追加。既存機能(F-01〜F-06)のコードはインデックス追加以外変更していない。バックエンド149件(既存127件+新規22件)・フロントエンド37件(既存30件+新規7件)のテストが全件成功、`tsc -b`・`npm run build`も成功を確認。 | イテレーション2 |
