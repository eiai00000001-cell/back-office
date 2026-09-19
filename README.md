# 個人事業(EIAI TEC)向け事務管理システム

## 1. 文書情報

- 作成日: 2026-09-16 / 改訂日: 2026-09-19
- 版数: 3.0-stage2(イテレーション3・段階2: リマインダー/通知 F-09・レポート出力 F-10 追加。段階3〔F-11 経営管理〕は未着手)
- 参照元:
  - `docs/02_architect/詳細設計書.md`(版数3.7。段階2は3.16〜3.18章・4.10・4.11・4.13・5・6.5・7・8章)
  - `docs/02_architect/基本設計書.md`(版数3.4。段階2は4.17〜4.19章)
  - `docs/02_architect/mockups/`(SC-01〜SC-18。段階2ではSC-16〜18と、SC-01の通知エリア・導線カード)
  - `docs/01_requirements/機能仕様書.md`・`要件定義書.md`
  - `docs/03_develop/レビュー結果報告書.md`(イテレーション1〜3・段階1分。9章の指摘14〜19に対応済み)
- 対応イテレーション: イテレーション1(初回実装、レビュー指摘対応を含む)、イテレーション2(財務ダッシュボード F-07 / SC-12 追加)、イテレーション3・段階1(案件・プロジェクト管理 F-08 / SC-13〜15 追加、起動時マイグレーション自動適用、レビュー指摘14〜19対応)、イテレーション3・段階2(F-09 通知 / SC-16・17、F-10 レポート出力 / SC-18、F-07集計の共通化、SC-01の通知エリア・導線カード)

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
      models/               … SQLAlchemy宣言的モデル(11テーブル。段階2で`reminder_deadlines`・`notification_acknowledgements`を追加)
      schemas/               … Pydanticスキーマ(リクエスト/レスポンス)
      repositories/           … DBアクセス層
      services/                … 業務ロジック層(税計算・採番・入金判定・変換・財務ダッシュボード集計等)
      routers/                  … APIルーター(FastAPI APIRouter。`dashboard.py`はイテレーション2で追加)
      utils/                     … 共通ユーティリティ(`date_range.py`: 直近12ヶ月算出・`build_month_keys`・`add_years`・`period_to_dates`、`csv_writer.py`: UTF-8 BOM付きCSV、`due_state.py`)
      templates/                 … PDF生成用Jinja2テンプレート
      dependencies.py             … DI(ルーター→サービス→リポジトリの組み立て)
      config.py                    … パス設定(db/・data/の場所解決)
      database.py                   … SQLAlchemy Engine/Session
      main.py                        … アプリ起動・例外ハンドラ・静的配信
    alembic/                  … DBマイグレーション(初回スキーマ+company_profile初期データ投入、イテレーション2で財務ダッシュボード向けインデックス追加リビジョンを追加)
    scripts/                  … launch.sh(起動前にマイグレーションを自動適用) / stop.sh(起動.app・終了.app から呼び出し)
    tests/                    … pytest(単体・APIレベル結合テスト)
    static/                   … npm run build の生成物の配置先(gitignore対象)
    data/attachments/          … (未使用。実際の添付ファイルは3.3節参照)
  frontend/                 … React + TypeScript(Vite)
    src/
      api/                    … Axiosベースのバックエンド呼び出し(`__tests__/`にVitestテスト。`dashboard.ts`はイテレーション2で追加)
      pages/                   … SC-01〜SC-18に対応する画面(段階2で`NotificationListPage`・`DeadlineListPage`・`ReportExportPage`を追加)(`__tests__/`にVitest+Testing Libraryのコンポーネントテスト。`DashboardPage.tsx`はイテレーション2で追加)
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

#### マイグレーションの自動適用(イテレーション3・段階1、レビュー指摘14対応)

`起動.app`(`backend/scripts/launch.sh`)は、Uvicornを起動する前に`python -m app.migrate`を実行し、未適用のAlembicマイグレーションを自動適用します。手動で`alembic upgrade head`を実行する必要はありません(実行しても問題ありません)。

- 適用済みなら何もしません(冪等)。
- 未適用がある場合は、適用前に対象DBを`db/back_office.db.before-<適用後のリビジョン>`(例: `db/back_office.db.before-a1c3f5e7b901`)へ退避コピーします。同名の退避コピーが既にある場合は上書きしません。
- DBファイルが存在しない場合は新規に作成して適用します(退避コピーなし)。
- 退避コピーは一時名(`.tmp`)へ作成し、成功後にリネームします(途中で失敗しても不完全なコピーは「作成済み」とみなされません)。
- `alembic_version`が無く`create_all()`のみで作られたDB(テーブルは存在)は、構造が既知リビジョンのいずれかと一致すると確認できた場合に限り、退避コピー後にそのリビジョンへ`stamp`してから`upgrade head`します。一致を確認できない場合は何も変更せず、日本語の専用案内を表示して起動を中止します。
- 二重起動は`backend/run/launch.lock`(`mkdir`ロック+PID記録)で排他します。2回目の起動は待機してブラウザを開くだけです。異常終了で残った古いロックはPIDの生死で検知し自動で解除します。
- 適用に失敗した場合は、失敗理由(1行)と`backend/logs/uvicorn.log`の案内を日本語のダイアログで表示し(詳細・Alembicログはログへ記録。ダイアログ表示自体に失敗した場合もログへ記録)、アプリ本体は起動しません。退避コピーから`db/back_office.db`へ戻して復旧できます(ダウングレードは提供しません)。
- リビジョン`a1c3f5e7b901`の内容: `projects`テーブル作成+`invoices`/`quotes`/`expenses`へ`ALTER TABLE ... ADD COLUMN project_id`(直接SQL。テーブル再作成なし)+インデックス作成。既存行の`project_id`はNULLのまま。旧版の起動時`create_all()`で先に`projects`が作成されたDBでも、再実行しても失敗しません。
- リビジョン`c4d8e2f6a715`(段階2)の内容: `reminder_deadlines`・`notification_acknowledgements`テーブルと`idx_reminder_deadlines_due_date`の作成のみ(`CREATE TABLE IF NOT EXISTS`。既存テーブルの変更・再作成なし)。旧版の`create_all()`で先に作成されたDBでも、再実行しても失敗しません。
- 段階1適用済みDB(`a1c3f5e7b901`)・段階1未適用DB(`2e1e85c3b7cc`。現在の実DBはこの状態)のどちらからも`head`(`c4d8e2f6a715`)へ適用できます。適用前の退避コピーは`db/back_office.db.before-c4d8e2f6a715`になります。
- 確認: `cd backend && .venv/bin/python -m app.migrate`(適用済みなら「マイグレーションは適用済みです」)、または`alembic current`が`c4d8e2f6a715`であること。
- `main.py`はimport時にテーブルを作成しません(`create_all()`は廃止。スキーマ作成はAlembicマイグレーションのみ)。`uvicorn`を直接起動する場合は自動適用されないため、**必ず先に**`cd backend && .venv/bin/python -m app.migrate`(または`alembic upgrade head`)を実行してください(DBファイルが無い場合は新規作成して全リビジョンを適用します。実行せずに起動するとテーブルが無くAPIがエラーになります)。
- 過去の`create_all()`により一部テーブルだけ先に作成されたDB(例: `alembic_version`は旧リビジョンのまま、`projects`等が空で存在、`invoices`等に`project_id`列なし)も、マイグレーションが`IF NOT EXISTS`・列有無確認で冪等に適用するため失敗しません(コピーDBでテスト確認済み)。
- DBの場所は環境変数`BACK_OFFICE_DB_PATH`で差し替え可能です(未指定時は`db/back_office.db`)。テストは存在しない場所へ差し替えて実DBに接触しないことを保証しています(5.1参照)。

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
cd frontend && npm run build          # backend/static に生成物を出力(段階2の画面を本番構成へ反映するには再ビルドが必要。開発中は未実行)
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

| F-08 | 案件・プロジェクト管理(イテレーション3・段階1) | 実装済み | SC-13(一覧)/SC-14(カンバン、`@hello-pangea/dnd`、楽観的更新+失敗時ロールバック)/SC-15(詳細・編集・紐付けダイアログ・削除)。`ProjectService`・`ProjectLinkService`・`ProjectRepository`、`PUT /api/{invoices\|quotes\|expenses}/{id}/project`、F-04での案件引き継ぎ、SC-02〜05・07の案件欄/列、SC-01の「案件管理」カード。案件削除は書類の`project_id`をNULLへ戻す(書類・入金・明細は残る) |
| F-09 | リマインダー/通知(イテレーション3・段階2) | 実装済み | SC-16(通知一覧。確認済みも表示スイッチ・確認済み/未確認に戻す・種類別取得失敗の表示)/SC-17(期限の登録・編集・削除ダイアログ)。`NotificationService`+4提供クラス(`InvoiceDueProvider`・`QuoteExpiryProvider`・`ProjectDueProvider`・`DeadlineProvider`。表示時にサーバーで算出、スケジューラなし、7日前から表示、超過後も解消まで表示)、再表示条件(期限日変更・近い→超過)、解消済み確認記録の整理、`DeadlineService`(毎年繰り返しの翌年更新)、`GET /api/notifications`・`/summary`・`POST/DELETE /acknowledge`、`/api/deadlines`のCRUD。SC-01に通知エリア(上位5件、独立API。失敗は通知エリアのみ)と「通知・期限」カード。F-05の強調表示は維持し通知は元データ1件につき最大1件 |
| F-10 | レポート出力(イテレーション3・段階2) | 実装済み | SC-18。`GET /api/reports/{type}`(請求書・入金・見積・経費のCSV、月次損益PDF/CSV、案件別サマリーCSV、会計ソフト連携用汎用CSV。UTF-8 BOM付き・CRLF・数式防止・`X-Record-Count`・期間指定・0件時は項目名のみ)、`ReportService`+種類別Builder、`CsvWriter`、`PdfGenerationService.render_monthly_pl_report_pdf`。F-07の集計を`FinancialAggregationService`へ共通化(F-07のAPI・応答は不変)。SC-01に「レポート出力」カード |
| F-11 | 経営管理(段階3) | 未実装 | 段階3の対象(今回のスコープ外)。SC-19・20、`management_goals`、SC-01の「経営管理」カードは段階3で対応(現状は追加していない) |

イテレーション2時点の規模: 全12画面(SC-01〜SC-12)・全29 APIエンドポイント(+ヘルスチェック+財務ダッシュボード4本の合計34本)を実装済み。詳細設計書7章のAPI設計との対応は1:1。

---

## 5. テスト実行結果

### 5.1 バックエンド(pytest)

- 実行コマンド: `backend/.venv/bin/python -m pytest -q`
- 結果(イテレーション3・段階2、レビュー指摘37〜39対応後): **417 passed / 0 failed**(415件に2件を追加: 削除済み通知元の確認済み記録が404後も削除されること・`source_exists`例外の404変換〔`test_api_notifications.py`〕。既存テストの更新なし)。直前(指摘30〜36対応後): **415 passed / 0 failed**(395件に20件を追加: レポート期間の年範囲・上限〔`test_api_reports.py`〕8、CSVのタブ・CR・数値対象外〔`test_csv_writer.py`〕2、通知元なし・`source_exists`〔`test_notification_service.py`〕8〔パラメータ含む〕、通知確認API〔`test_api_notifications.py`〕2。既存テストの更新は`test_acknowledge_resolved_returns_404_with_message`のみ〔削除済みは別文言になったため、存在する対象外案件で解消済みを検証〕)。直前: **395 passed / 0 failed**(create_all廃止・通知タイトル修正後)(389件に6件を追加: 実DB非接触の検証3〔`test_no_real_db_access.py`〕、旧create_all由来の一部作成済みDBへの自動適用1、通知タイトル2)。実DB非接触の担保: `tests/conftest.py`がapp import前に`BACK_OFFICE_DB_PATH`を存在しない場所(`/nonexistent-back-office-guard/back_office.db`)へ設定し、全テストがそのパスで通る(実DBへ接続すれば失敗する)。加えてサブプロセスでの`app.main`import時にDBファイル・ディレクトリが作られないことを検証。直前: **389 passed / 0 failed**(段階1完了時の271件に118件を追加。内訳: CsvWriter 6、期間ユーティリティ 6〔`test_date_range_reports.py`〕、段階2マイグレーション 7〔旧スキーマ適用・制約・冪等・退避コピー・stamp・テーブル非再作成〕、DeadlineService 11〔毎年繰り返し・うるう日・確認記録の破棄を含む〕、通知サービス 29〔提供クラス4種・`_is_hidden`・並び順・種類ごとのエラー分離・解消済み整理・確認済み/再表示条件・繰り返し期限の更新〕、期限API 11、通知API 11、共通集計 6、レポートサービス 19〔7種の内容・並び・ラベル・数式防止・空データ・PDF・件数一致〕、レポートAPI 12)。既存271件は無修正で全件成功。直前(段階1、必須欠落・文字数超過の日本語化後): **271 passed**(`test_validation_messages_ja.py`27ケースを追加)。直前(ID項目の型エラー日本語化後): **244 passed**(`test_id_range.py`に数値以外のID入力の検証12件を追加)。直前(ID範囲違反の日本語メッセージ化後): **232 passed**(`test_id_range.py`にメッセージ検証2件を追加)。直前(テスト不具合#1・#2修正後): **230 passed**(`test_id_range.py`を17件追加〈ID入力の範囲検証〉)。直前(レビュー指摘24〜27対応後): **213 passed**(指摘24〜27対応で`test_launch_script.py`5件・`test_migration_runner.py`3件を追加)。指摘20〜23対応後は**205 passed**(指摘20〜23対応で`test_migration_runner.py`6件・`test_launch_script.py`4件を追加。直前は195件。段階1初版の186件+`test_migration_runner.py`6件〈自動適用・退避コピー・冪等・上書きなし・新規DB・失敗時〉+納期形式2件+適用前後のF-07/home一致1件)。段階1初版時点: **186 passed**(既存149件+F-08の新規37件、失敗0件。新規は`test_api_projects.py`〈CRUD・並び順・フィルタ・件数・納期状態・ステータス変更・詳細集計・削除・紐付けAPI・通常PUTの`project_id`・F-04引き継ぎ〉、`test_due_state.py`、`test_migration_project.py`〈既存データ入りDBへの適用で件数・金額・子データ不変、冪等性、案件削除時のSET NULL〉)。以下はイテレーション2時点の記録: **149 passed**(TDDによる単体テスト+APIレベル結合テスト、失敗0件。イテレーション1の127件+イテレーション2で追加した22件)
- 内訳(主なテスト対象): `TaxCalculationService`・`NumberingService`・`PaymentService`(入金ステータス・期限超過判定・入金登録)・`InvoiceService`・`QuoteService`・`QuoteToInvoiceConversionService`(1対1制約・独立性)・`ExpenseService`(期間From/Toバリデーションを含む)・`AttachmentService`(拡張子・サイズ検証、パストラバーサル拒否、添付ファイル削除)・`HomeSummaryService`・`PdfGenerationService`(WeasyPrint実PDF生成)・`ClientService`・`CompanyProfileService`、`main.py`の例外ハンドラ(バリデーションエラーの日本語メッセージ整形・予期しない例外のログ記録)、および全ルーターのAPI結合テスト(clients/company-profile/invoices/quotes/expenses/payments/home/health/dashboard)
- イテレーション2追加分: `build_last_12_months`/`month_start`/`month_end`(`tests/test_date_range.py`、年またぎ・うるう年を含む7件)、`DashboardService`(`tests/test_dashboard_service.py`、月次売上・入金額・経費・損益・見積件数金額の集計、issue_date NULLの除外、月次0円/0件補完、見積成約率の算出・0除算回避の10件)、財務ダッシュボードAPI(`tests/test_api_dashboard.py`、4エンドポイントの疎通・実データ反映の5件)

### 5.2 フロントエンド(Vitest)

- 実行コマンド: `frontend && npx vitest run`
- 結果(イテレーション3・段階2、指摘39対応後): **100 passed / 0 failed**(99件に1件を追加: 年範囲違反と開始>終了が同時のとき年範囲メッセージを優先〔`ReportExportPage.test.tsx`〕。既存テストの更新なし)。直前(指摘36対応後): **99 passed / 0 failed**(91件に8件を追加: 空データ文言の種類別7〔明細系5種・月次損益CSV・月次損益PDF〕、年範囲・120か月超の入力エラー1。既存の文言テスト1件は新文言へ更新)。直前: **91 passed / 0 failed**(既存58件に33件を追加: `HomePage`〔通知エリア・独立取得・確認済み・導線カード〕8、`NotificationListPage`8、`DeadlineListPage`7、`ReportExportPage`9、`defaultReportPeriod`1)。直前(段階1、テスト不具合#1修正後): **58 passed**(`utils/__tests__/items.test.ts`4件、`InvoiceDetailPage`・`QuoteDetailPage`に数量が文字列の回帰各1件を追加。両画面の既存モックも実API形式の`'1.00'`へ変更)。直前(段階1時点): **52 passed**(既存37件+新規15件〈`ProjectKanbanPage`4件、`ProjectDetailPage`6件、`InvoiceDetailPage`・`QuoteDetailPage`・`ExpenseFormPage`への案件欄の回帰5件〉、失敗0件)。以下はイテレーション2時点の記録: **37 passed**(失敗0件。イテレーション1の30件+イテレーション2で追加した7件)
- 内訳: `calculateTotals`/`calculateItemAmount`(サーバー側`TaxCalculationService`と同一ロジックのフロントエンド版、詳細設計書4.1ステップ6のリアルタイム表示要件に対応)、`formatCurrency`/`isOverdueDate`(表示フォーマット共通処理)、`extractErrorMessage`(配列形式detailへの防御的処理)、`InvoiceDetailPage`(保存・入金登録・超過確認ダイアログ・取引先「新規登録」リンク遷移・`selectedClientId`復帰のコンポーネントテスト)、`QuoteDetailPage`(取引先「新規登録」リンク遷移・`selectedClientId`復帰のコンポーネントテスト)、`ExpenseFormPage`(添付ファイル検証・保存ボタン活性制御のコンポーネントテスト)
- イテレーション2追加分: `formatMonthLabel`/`formatLast12MonthsRangeLabel`(`src/utils/__tests__/format.test.ts`、4件)、`DashboardPage`(`src/pages/__tests__/DashboardPage.test.tsx`、全区画正常表示・区画単位のエラー分離表示・見積成約率0除算時の「-」表示の3件)

### 5.3 TypeScriptビルド・ESLint相当

- イテレーション3・段階2: `npx tsc -b`成功。ビルドは出力先を一時ディレクトリへ変えて(`npx vite build --outDir <一時>`)成功を確認し、`backend/static`は未更新(既存の生成物を置き換えないため)。
- イテレーション3・段階1: `npx tsc -b`・`npm run build`ともに成功(`@hello-pangea/dnd`を`frontend/package.json`へ追加)。

- `npx tsc -b`: エラーなし(Recharts v3のTooltip formatter/labelFormatter型に合わせて型安全なラッパー関数を用意)
- `npm run build`: 成功(`backend/static`に生成物出力を確認)

---

## 6. 詳細設計書との差異

| # | 項目 | 詳細設計書の記載 | 実装内容 | 理由 |
|---|---|---|---|---|
| 1 | Pythonバージョン | 3.12 | 3.13.3(pyenv) | 開発環境にPython 3.12がインストールされておらず、3.11(Homebrew)より新しい3.13を採用。FastAPI/SQLAlchemy/WeasyPrint等、使用ライブラリはいずれも3.13対応済みで、動作確認上の問題は発生していない。EIAI TEC本人の実機セットアップ時にPython 3.12が利用可能であれば、`backend/.venv`を3.12で作成し直すことで詳細設計書の記載どおりに戻せる(コード変更は不要)。 |
| 2 | 添付ファイル保存先パス(4.2章) | `backend/data/attachments/expenses/{expense_id}/...` | プロジェクトルート直下の`data/attachments/expenses/{expense_id}/...`(`backend/`配下ではない) | 詳細設計書2章・基本設計書3章・7章は「データ保存場所はプロジェクトフォルダ配下の`db/`・`data/`」と明記しており、基本設計書のシステム構成図でも`db`・`Files`(添付・PDF)はバックエンドプロセスと並列のノードとして描かれている。4.2章の具体パス記載とこの全体方針との間に軽微な不整合があったため、後者(基本設計書のシステム構成方針)を優先し、プロジェクトルート直下の`data/`配下に統一した。DBファイルも同様に`db/back_office.db`とし、`backend/app/config.py`で絶対パス解決している(cwdに依存しない)。 |
| 3 | データベースマイグレーション | Alembicでスキーマ変更履歴を管理(基本設計書2.1章) | Alembicの初期マイグレーション(`backend/alembic/versions/`)を作成し、`company_profile`への初期データ投入(詳細設計書6.3章)もマイグレーション内で実施。(当初は`main.py`起動時の`Base.metadata.create_all()`も併用していたが、2026-09-19に廃止しAlembicへ一本化。要確認事項#14) | 単一ユーザーの個人利用アプリという性質上、開発時の取り回しやすさを優先し、Alembicの初回マイグレーション整備と並行してcreate_all()による自動テーブル作成も残した。今後のスキーマ変更は新規Alembicリビジョンとして追加する運用を想定。 |
| 4 | フロントエンドのフォーム実装 | 明記なし(React Hook Form + Zodを採用技術として選定、基本設計書2.1章) | 取引先マスタ・システム設定画面はReact Hook Form + Zodで実装。請求書・見積書・経費の画面は、品目明細の動的な行追加・削除を伴う複雑なフォームのため、Reactの`useState`による素朴な状態管理で実装 | RHFのフィールド配列(useFieldArray)を用いた実装も可能だが、開発規模とのバランスを考慮し、複雑な動的配列フォームは素朴な状態管理を採用した。挙動・バリデーション内容は詳細設計書3章の入力項目定義表に準拠している。 |
| 5 | SC-09売掛金一覧の「入金済み金額」列 | API設計(7章)の`InvoiceListItemResponse`に入金済み金額は明記なし | `InvoiceListItemResponse`に`paid_amount`(入金済み金額の合計)を追加 | 基本設計書4.10章の画面レイアウトおよびmockup(SC-09)に「入金済み金額」列が明記されているため、API設計を実装レベルで補完した。仕様の追加ではなく、既存の確定仕様(mockup)をAPIに反映したものである。 |
| 6 | SC-12損益(収支)区画の凡例文言(イテレーション2) | mockup(`SC-12_financial-dashboard.html`)は赤字月の凡例に「例: 26/1」というダミーデータ固有の月を含む | 「赤字月(売上-経費 < 0円)」とし、ダミーデータに紐づく具体的な月の例示は含めない | mockupの当該箇所はダミーデータ(2025年10月〜2026年9月の架空の集計値)に基づく例示であり、実データでは同じ月が赤字になるとは限らないため、実装では一般化した文言とした。基本設計書4.13章の要求(黒字・赤字を視覚的に区別する配色)自体は満たしている。 |
| 7 | SC-12各区画の読み込み中表示(イテレーション2) | mockupは読み込み完了後の表示例とエラー時表示例(コメントアウト)のみを示し、読み込み中の状態については明記なし | 各区画のデータ取得中は「読み込み中です…」という簡易な状態表示を追加 | 4区画が独立してAPIを呼び出す構成(4.8.6章)のため、取得完了までの間、区画ごとに空白のカードが表示され続けることを避ける目的で、最小限の状態表示を追加した。新しい装飾やレイアウトの追加ではなく、既存のエラー表示(「情報を取得できませんでした」)と対になる一時的な文言に留めている。 |
| 8 | 案件の存在しないIDのエラー(イテレーション3) | 422(4.9.5) | 新設の`UnprocessableError`で422を返す | 既存の`ValidationFailedError`は400にマップされているため、既存挙動を変えずに設計どおり422にするため |
| 9 | `ProjectRepository.delete`(4.9.6) | 書類の`project_id`をNULLへ更新→案件削除。設計5.3章は各書類リポジトリの`clear_project`等を想定 | 書類の一括更新は`ProjectRepository.delete`内で実施(`set_project`/`clear_project`等は作らず、紐付けは`ProjectLinkService`が直接更新) | 段階1では呼び出し元が案件削除と紐付けのみで、リポジトリメソッドの追加が過剰なため。`sum_total_by_project`等は段階3で追加する想定 |
| 10 | 取引先削除時の案件による削除不可(4.13.2・8章) | 案件が紐付く取引先は削除不可(409)、文言に「案件」を含める | 対応せず | 現行実装には取引先の削除APIが存在しない(`clients`は登録・更新・参照のみ)ため。DB側は`projects.client_id`の外部キー(RESTRICT)のみ。**将来、取引先削除機能を追加する際は、案件が紐付く場合は削除不可(409、文言に「案件」を含める)とする要件を必ず適用すること**(要確認事項#10) |
| 11 | `app/core/constants.py`のうち`HOME_NOTIFICATION_LIMIT` | 段階2のため対象外 | 段階2で`HOME_NOTIFICATION_LIMIT = 5`を追加(解消) | 段階2で対応 |
| 12 | Alembic `env.py` | 記載なし | `config.attributes["database_url"]`があれば接続先として優先(なければ従来どおり) | 既存データ入りのテスト用DBへ適用するマイグレーションテストのため。通常のコマンド実行には影響しない |
| 13 | 起動時のマイグレーション自動適用(レビュー指摘14、ユーザー確定) | 詳細設計書4.13.1-5「起動処理は既存実装に従う」 | `launch.sh`が起動前に`python -m app.migrate`(`app/migration_runner.py`)を実行し、適用前にDBを退避コピー、失敗時は起動中止 | 未適用のまま起動すると既存機能が全面的に失敗するため。詳細設計書への反映(4.7.3起動処理・4.13.1)はarchitectへ依頼が必要 |
| 14 | 案件の納期(`due_date`)検証(レビュー指摘15) | 日付として妥当であること | `YYYY-MM-DD`形式に厳格化し、`isoformat()`で正規化して保存 | `fromisoformat`が`20260919`等も受理し、TEXT比較・期限判定が崩れるため |
| 15 | 案件存在検証の`project_repository`(レビュー指摘16) | 記載なし | `InvoiceService`/`QuoteService`/`ExpenseService`で必須引数化(既存テストを更新) | 渡し忘れで検証が黙ってスキップされるのを防ぐため |
| 16 | マイグレーション自動適用の追加仕様(レビュー指摘20〜23) | 差異#13のとおり | 失敗理由のみのダイアログ+ログ案内、`alembic_version`無しDBの安全なstamp(構造一致時のみ)、退避コピーの一時名→リネーム、`launch.lock`による二重起動排他。`alembic/env.py`は`configure_logger`属性でログ設定を抑止可能に | 指摘20〜23への対応。詳細設計書4.7.3.1(起動処理)への反映もarchitectへ依頼が必要(差異#13に含める) |
| 17 | 起動処理の追加仕様(レビュー指摘24〜27) | 差異#13・#16のとおり | ロックの競合対策(PID未記入の猶予・mvによる原子的解除・300秒超過で古いロック扱い)、ロック取得後のヘルス再確認、UTF-8ロケール設定、stamp判定に既定値・UNIQUEを追加(CHECK・ON UPDATE・トリガは比較対象外)、stamp後のupgrade失敗時の復元案内 | 指摘24〜27への対応。詳細設計書4.7.3.1〜4.7.3.3への反映もarchitectへ依頼が必要(差異#13に含める)。許容する制約: ロック解除の再取得が完全な原子性を持つわけではなく、解除直後に他者が取得し直す極めて短い窓は残る(単一利用者では実害なし) |
| 18 | SC-16・SC-01の通知の状態表示・種類名(段階2) | 詳細設計書4.10.4の状態遷移図は「期限が近い」「期限超過」、4.10.2は種類を`INVOICE_DUE`等の識別子で記載 | mockupに合わせ、状態は塗りつぶしバッジ「超過」「接近」、種類は「請求書の支払期限」「見積書の有効期限」「案件の納期」「登録した期限」で表示 | 依頼指示(mockup準拠)。状態遷移の判定ロジック自体は設計書どおり |
| 19 | 通知の`title`文言(段階2) | 4.10.2: 案件=`案件「{name}」の納期`、期限=`{name}`(種別ラベルを付記) | 設計書の形式を採用(案件=`案件「{name}」の納期`、期限=`{name}({種別ラベル})`。ただし名称と種別ラベルが同一なら名称のみ)。mockupの例(「{name} の納期」「契約更新(サンプル保守契約)」)とは表記が異なる | 設計書が実装の正のため。名称=種別の重複のみ解消済み(要確認事項#13) |
| 20 | `FinancialAggregationService.expense_by_category`(4.12.1) | `dict[str,int]`を返す | 辞書版に加え、件数を含む`expense_category_rows`(科目・件数・合計)を公開し、`DashboardService`はこちらを使用 | F-07の勘定科目別内訳の応答が`count`を含むため(F-07の外部仕様を変えないための補完) |
| 21 | レポート用リポジトリ(5.3) | 種類別のレポート作成クラスが各Repositoryを呼ぶ | 一覧系・案件別サマリーの読み取りクエリを`ReportRepository`に新設して集約(`ExpenseRepository.aggregate_by_month_and_category`は設計どおり追加) | クエリの置き場所が設計書に明記されておらず、読み取り専用の出力用クエリを1か所にまとめるため |
| 22 | `DeadlineResponse.due_state`(7章) | `DeadlineResponse`の項目に明記なし | `due_state`(OVERDUE/UPCOMING/null。`judge_due_state`)を追加 | mockup SC-17の「接近」タグ表示のため。既存項目は不変 |
| 23 | 期限・レポートの入力検証メッセージ(8章) | 名称・期限日未入力の文言のみ規定 | 期限日は`YYYY-MM-DD`形式に厳格化(「期限日は日付(YYYY-MM-DD)で入力してください」)、名称・期限日はキー欠落も「〜を入力してください」。レポートの年月形式不正は「年月はYYYY-MM形式で指定してください」、出力形式不正は「出力形式はcsvまたはpdfを指定してください」、未知の種類は404、`period_from`・`period_to`の片方のみ指定は不足側に既定値(直近12ヶ月の端)を補完 | 設計書に文言・扱いの記載がない入力パターンの補完(422/404の統一) |
| 24 | 元データ削除時の確認済み記録の削除(4.10.4) | 元データの削除時に対応する記録を削除 | サービス層でなく`InvoiceRepository.delete`・`QuoteRepository.delete`・`ProjectRepository.delete`内で`delete_acknowledgement`を実行(期限は`DeadlineService`)。既存サービスのコンストラクタを変えないため | 既存テスト・DIを変えずに実現するため |
| 25 | SC-01の「経営管理」カード | 3.21章: 経営管理カード→SC-19 | 段階3のため追加していない(mockupは`href="#"`の仮リンク) | 依頼指示(段階3で対応) |
| 26 | 不正な`source_type`・型不正の422 | 8.1章の既知の制約(英語のまま) | 通知確認APIの`source_type`不正もPydantic標準の英語メッセージのまま(欠落は「通知の種類は必須です」) | 8.1章の方針(型不正は対象外)に従う |
| 27 | 片方のみ指定時の期間判定の例示(4.11.1、指摘30・31) | 例として「`period_to=2099-12`のみ指定→開始は現在月の11か月前に補完され、開始>終了のため422」 | 補完した開始(現在月の11か月前)は2099-12より前のため開始>終了にならず、上限(120か月)超過の422「期間は最大120か月(10年)以内で指定してください」となる(422である点は設計と同じ。設計書の例示の誤りと判断) | 設計書の記述の誤りの可能性(architectureへ確認を依頼) |

### 6.1 運用ルール: Alembicと`create_all()`の併用について

(2026-09-19改訂: `main.py`の`create_all()`は廃止済み。スキーマ作成・変更はAlembicのみ。)従来の`create_all()`は「存在しないテーブルを作成する」だけで、既存テーブルへのカラム追加・型変更等は一切反映しなかった。**今後のイテレーションでSQLAlchemyモデルに変更(カラム追加・型変更・制約変更等)を加える場合は、必ず対応するAlembicリビジョンを`backend/alembic/versions/`に追加すること**を運用ルールとして明文化する(レビュー結果報告書 指摘5対応)。スキーマ変更の管理主体はAlembicのみとする。リビジョン追加を怠ると、アプリのコードが期待するスキーマと実際のDBスキーマが起動時エラーにならずに静かに乖離し、該当カラムへのアクセス時点で初めて例外になるおそれがある。

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
| 7 | (イテレーション3・段階1)`ExpenseFormPage`等でカンバンのドラッグ&ドロップ自体(マウス操作)はjsdomでの自動テストが困難なため、`onDragEnd`はテストせず「ステータス変更」メニュー経由(同一の`changeStatus`処理)で楽観的更新・ロールバックを検証した | 中(実際のドラッグ操作) | ブラウザでのドラッグ&ドロップ操作をtesterが実機確認 | tester | 段階1テスト時 |
| 8 | (イテレーション3・段階1)実DB(`db/back_office.db`)へのマイグレーションは未適用(コピー・テスト用DBでの適用のみ確認)。実DBの`alembic_version`は`2e1e85c3b7cc`(読み取りのみで確認済み。コピーへの適用も成功)のためstampは不要。次回`起動.app`の起動時に自動適用される(3.1参照)ため、初回起動後に`db/back_office.db.before-a1c3f5e7b901`の作成と`alembic current`を確認する | 中 | 初回起動後に確認(自動適用の実機確認は`起動.app`ダブルクリックを含めEIAI TEC本人/testerで実施) | project-leader/tester | 段階1納品時 |
| 12 | (イテレーション3・段階1)`launch.sh`のロック期限(既定300秒)・PID猶予(既定1秒)、ロケール選択(`en_US.UTF-8`→`ja_JP.UTF-8`→`C.UTF-8`)は開発環境(`bash`スタブ)での確認のみ。`起動.app`(Finder起動)実機でのロケール・`stat`動作は未確認 | 低 | EIAI TEC本人の実機で`起動.app`から起動し、長い日本語エラー時のダイアログ表示を確認(要確認事項#2と合わせて) | EIAI TEC本人 | 納品フェーズまで |
| 10 | (将来要件)取引先削除機能を追加する際は、案件が紐付く取引先は削除不可(409、文言に「案件」を含める。詳細設計書4.13.2)とする | 低(現状は削除機能なし) | 取引先削除機能の追加時に適用 | architect/developer | 取引先削除機能の追加時 |
| 11 | `ProjectRepository.list_due_before`は段階2の通知(`ProjectDueProvider`)で使用(解消) | - | - | - | - |
| 9 | ★17〜26は2026-09-19に確定済み(詳細設計書3.5版)。段階2は確定内容のまま実装した | - | 詳細設計書9章・基本設計書8.3章を参照 | - | - |
| 13 | (解消)手動登録の期限の通知`title`は、名称と種別表示名が同一の場合は名称のみ(例: 「確定申告」)、異なる場合は`{名称}({種別})`。案件・請求書・見積書の文言は従来どおり。mockupの例示と設計書4.10.2の文言差は設計書側の判断に委ねる | - | 設計書4.10.2の改訂(architect) | architect | - |
| 14 | (解消)`main.py`の`create_all()`を廃止し、スキーマ作成をAlembicマイグレーションのみに一本化。テストは実DBパスを存在しない場所へ差し替えて実行。実DBには過去のテスト実行の副作用で空の`projects`・`reminder_deadlines`・`notification_acknowledgements`が存在し`alembic_version`は`2e1e85c3b7cc`のままだが、この状態を再現したコピーDBで自動適用が成功することをテスト済み(実DBには未接触) | 低 | 詳細設計書4.7.3(起動処理)・4.13.1の`create_all`前提記述の改訂(architect) | architect | - |
| 15 | (段階2)実DBへのマイグレーションは未適用(コピーDBに`a1c3f5e7b901`→`c4d8e2f6a715`を連続適用し、通知・期限・レポートAPIの疎通を別ポートで確認済み)。次回`起動.app`起動時に自動適用され、`db/back_office.db.before-c4d8e2f6a715`が作成される | 中 | 初回起動後に`alembic current`が`c4d8e2f6a715`であることと退避コピーの作成を確認 | tester/EIAI TEC本人 | 段階2納品時 |
| 16 | (段階2)フロントエンドの新画面(SC-16〜18、SC-01通知エリア)はjsdomのコンポーネントテストとAPI疎通のみ確認。ブラウザでの見た目・CSV/PDFのダウンロード保存、Excel等でのUTF-8 BOM付きCSVの文字化けなしの確認は未実施(`backend/static`も未再ビルド) | 中 | 本番ビルド後に実機で各画面とダウンロードを確認 | tester | 段階2テスト時 |

基本設計書8章・詳細設計書9章に記載の要確認事項はすべて確定済みであり、本書時点で持ち越しとなる新規の未解決事項はない(上記は本実装フェーズで新たに生じたもの)。

---

## 8. 変更履歴

| 版数 | 日付 | 内容 | 対応イテレーション |
|---|---|---|---|
| 3.0-stage2-r3 | 2026-09-19 | レビュー指摘37〜39に対応。(37)通知元が削除済みの確認時、確認済み記録の削除を`get_db`のロールバックで失わないよう、`NotificationService._find_candidate`で削除後に明示commitしてから404を返す(`get_db`・他APIの挙動は不変。API経由の再現テストで404後にも記録が残ることをRed確認済み)。(38)`provider.source_exists`の例外もcollectと同様にログ(種類・トレースのみ)して404「通知の元データが見つかりません」に変換。(39)`ReportExportPage.tsx`の判定順を年範囲→開始>終了→上限にサーバー・設計へ統一。テスト: pytest 417件・vitest 100件 | イテレーション3・段階2 |
| 3.0-stage2-r2 | 2026-09-19 | レビュー指摘30〜36に対応(詳細設計書3.7版)。(30・31)レポート期間の年範囲2000〜2099・上限120か月を`reports.py`に追加(定数は`core/constants.py`。判定順は詳細設計書4.11.1どおり)。(32)CSVの数式対策にタブ・CRを追加(数値型は対象外)。(33)通知確認で通知元が削除済み・取得失敗の場合は404「通知の元データが見つかりません」(提供クラスに`source_exists`を追加。削除済みなら残る確認済み記録を削除)。(34)マイグレーションのdocstring・READMEのcreate_all前提の記述を整理(処理内容・リビジョンIDは不変)、未使用の`config.DB_DIR`を削除。(35)テスト追加。(36)SC-18の空データ文言を種類別に変更、画面側でも年範囲・120か月超を入力エラー化。単一機能に閉じない修正(レポート・通知の2機能)のため、reviewerの再レビューが必要。 | イテレーション3 |
| 3.0-stage2-r1 | 2026-09-19 | 要確認事項#13・#14に対応。(#14)`main.py`の`create_all()`を廃止しスキーマ作成をAlembicのみに一本化、`database.py`のimport時ディレクトリ作成を廃止、`config.py`にDBパスの環境変数`BACK_OFFICE_DB_PATH`を追加、`tests/conftest.py`で実DBパスを存在しない場所へ差し替え、実DB非接触・新規DB全リビジョン適用・旧create_all由来DBへの適用のテストを追加。(#13)手動期限の通知タイトルで名称=種別表示名の場合は名称のみとした。pytest 395件・vitest 91件成功。単一機能に閉じた修正(設計書4.7.3・4.10.2への反映はarchitectへ依頼) | イテレーション3・段階2 |
| 1.0 | 2026-09-16 | 初版作成。詳細設計書1.1・基本設計書1.2・mockups(SC-01〜SC-11)をもとに、バックエンド(FastAPI、4層構成、8テーブル、29+1 APIエンドポイント、TDDによるpytestテスト108件)・フロントエンド(React 18 + TS + Vite + MUI、全11画面、Vitestテスト13件)・起動/終了.appのビルド一式を実装。 | イテレーション1(初回) |
| 1.1 | 2026-09-16 | `docs/03_develop/レビュー結果報告書.md`(版数1.0)の指摘のうちコード修正で対応可能な11件(高2件・中4件・低5件)に対応。主な内容: (1)バリデーションエラー時の422応答を単一の日本語文字列`detail`に整形する`RequestValidationError`ハンドラを追加し、`InvoiceItemInput`等の主要スキーマにField(description=...)の代替となる`field_validator`を追加、フロントエンド`extractErrorMessage()`に配列形式detailへの防御的処理を追加、`ItemsEditor`利用画面(請求書/見積書)に保存前チェック・保存ボタン活性制御を追加。(2)経費領収書アップロードのパストラバーサル対策(`AttachmentService`にファイル名検証を追加)。(3)予期しない例外を`logging.exception`でUvicornエラーログへ記録。(4)経費一覧の期間(From/To)バリデーションをフロント・バックエンド双方に追加。(5)Alembic運用ルールを本書6.1節に明文化。(6)`InvoiceDetailPage`・`ExpenseFormPage`にTesting Libraryによるコンポーネントテストを追加。(8)`InvoiceRepository.exists_by_source_quote_id`に設計書対応関係のコメントを追加。(9)`ItemsEditor`の行`key`を`crypto.randomUUID()`ベースの安定IDに変更。(10)経費削除時に添付ファイル実体も削除する処理を追加。(11)`ClientMasterPage`の呼び出し元復帰遷移を`useNavigate()`によるクライアントサイド遷移に置き換え。バックエンド127件・フロントエンド26件のテストが全件成功することを確認済み。指摘7(`backend/data/attachments/.gitkeep`削除)・指摘12(詳細設計書パス記載更新)は対象外(前者はファイル削除のためユーザー許可待ち、後者はarchitectフェーズ対応)。 | イテレーション1(レビュー指摘対応) |
| 1.2 | 2026-09-16 | `docs/04_test/テスト結果報告書.md`(版数1.0)で不合格となったTC-C06(重大度: 高、取引先マスタ画面SC-10への遷移導線欠落)に対応。詳細設計書3.3章・3.5章およびmockup(SC-03/SC-05)のとおり、`InvoiceDetailPage.tsx`・`QuoteDetailPage.tsx`の取引先選択欄(`Autocomplete`)の隣に「新規登録」インラインリンク(`/clients?returnTo=<現在のパス>`へ遷移)を追加し、`ClientMasterPage.tsx`側の既存の呼び出し元復帰ロジック(`?selectedClientId=<id>`付きでの復帰)に対応する形で、両画面に`selectedClientId`クエリパラメータ受け取り時の取引先選択状態復元処理を追加した。TDD方針に基づき、先にコンポーネントテスト(`InvoiceDetailPage.test.tsx`へのテスト追加2件、新規`QuoteDetailPage.test.tsx`2件)をRed状態で作成してから実装し、Green化を確認した。バックエンド127件(影響なし・変更なし)・フロントエンド30件(既存26件+新規4件)のテストが全件成功。単一機能に閉じたフロントエンドの結線修正のため、設計整合性への影響はなく、reviewerへの再レビュー依頼は不要と判断し、testerの実機再確認に委ねる。 | イテレーション1(テスト指摘対応) |
| 3.0-stage1 | 2026-09-19 | イテレーション3・段階1: F-08(案件・プロジェクト管理)を実装。バックエンド: `projects`テーブル・`project_id`列追加(Alembic `a1c3f5e7b901`、直接ALTER TABLE)、案件CRUD・ステータス変更・詳細集計・削除、紐付け専用API、F-04での案件引き継ぎ、請求書/見積書/経費のPOST/PUT・レスポンスに`project_id`/`project_name`。フロントエンド: SC-13〜15、SC-02〜05・07の案件欄/列、SC-01の「案件管理」カード。回帰確認(詳細設計書4.13.2)は既存テスト149件+フロント既存37件の全件成功で確認。単一機能に閉じるため、reviewerの段階1レビューを依頼予定。 | イテレーション3(段階1) |
| 3.0-stage2 | 2026-09-19 | イテレーション3・段階2: F-09(リマインダー/通知)・F-10(レポート出力)を実装。バックエンド: Alembic `c4d8e2f6a715`(`reminder_deadlines`・`notification_acknowledgements`、テーブル再作成なし・冪等)、`NotificationService`+4提供クラス、`DeadlineService`(毎年繰り返し)、`ReportService`+7種のBuilder、`CsvWriter`、月次損益PDF(`monthly_pl_report.html`)、`FinancialAggregationService`(F-07の集計を共通化。`DashboardService`はこれへ委譲し、F-07のAPI・応答は不変)、`/api/notifications`・`/api/deadlines`・`/api/reports/{type}`、`field_labels.py`への項目名追加。フロントエンド: SC-16・17・18、SC-01の通知エリア(独立取得)と導線カード2枚。TDD(先にテストを書きRed確認→実装→Green)。テスト: pytest 389件(+118)・vitest 91件(+33)、既存テストは無修正で全件成功。回帰: F-07の4API・`home/summary`・ID範囲検証・日本語化メッセージ等は既存テストで確認。再レビュー要否: 段階2は新規機能でありreviewerの段階2レビューを依頼予定(複数機能にまたがる変更は`DashboardService`のみ〔委譲化〕) | イテレーション3(段階2) |
| 3.0-stage1-r7 | 2026-09-19 | 422の必須項目欠落(`Field required`)と文字数超過(`String should have at most N characters`)を日本語化(「◯◯は必須です」「◯◯はN文字以内で入力してください」)。`app/main.py`の`RequestValidationError`ハンドラで`type`(missing・string_too_long)と`loc`から組み立て、項目名の対応表は`app/schemas/field_labels.py`に一元管理(画面ラベルに準拠、同名項目は`request.url.path`で上書き)。ボディ全体が空の場合は「入力内容を確認してください」。既存の日本語メッセージ・型不正の挙動は不変、既存テストの修正なし。テスト: pytest 271件(+27)・vitest 58件。詳細設計書8章(エラーハンドリング)へ反映が必要 | イテレーション3・段階1 |
| 3.0-stage1-r6 | 2026-09-19 | ID項目に数値以外(`/api/clients/abc`、`?client_id=abc`、ボディの`"project_id": "abc"`等)を渡した際のPydantic標準の英語メッセージ(`int_parsing`等)を「IDの値が正しくありません」に統一。`app/main.py`の既存`RequestValidationError`ハンドラで、フィールド名が`id`/`*_id`かつ型エラー(`int_parsing`・`int_type`・`int_from_float`・`int_parsing_size`)の場合に置き換える(ID以外の項目の挙動は不変)。テスト: pytest 244件(+12)・vitest 58件 | イテレーション3・段階1 |
| 3.0-stage1-r5 | 2026-09-19 | ID範囲違反(0・負数・2^63-1超)の422`detail`をPydantic標準の英語から「IDの値が正しくありません」に変更。`EntityId`を`Field(ge,le)`から`AfterValidator`(`ValueError`)方式に変更し、既存の`RequestValidationError`ハンドラ(`Value error, `除去)でパス・クエリ・ボディの全適用箇所が日本語になる。`app/main.py`は変更なし。テスト: pytest 232件・vitest 58件 | イテレーション3・段階1 |
| 3.0-stage1-r4 | 2026-09-19 | テスト結果報告書の不具合#1・#2に対応。(#1・高)APIはDecimalの`quantity`を文字列(`"1.00"`)で返すが`validateItems`は`Number.isFinite`で判定していたため、既存の請求書・見積書を開くと保存ボタンが無効のままだった。`utils/items.ts`の`toItemInputs`で取得時に数値へ正規化(`ItemResponse`型を`number | string`とし正規化漏れをコンパイル時に検出)。(#2・低)`schemas/common.py`に`EntityId`(1〜2^63-1の整数)を追加し、請求書・見積書・経費・案件・紐付けのリクエストのID項目、およびパス・クエリのID引数へ適用(範囲外は500でなく422)。単一機能に閉じない軽微な横断修正(バックエンドの入力検証とフロントの取得値変換のみ、設計上の仕様変更なし)のためtesterの再確認に委ねる。テスト: pytest 230件・vitest 58件 | イテレーション3・段階1 |
| 3.0-stage1-r3 | 2026-09-19 | レビュー結果報告書9.8節(指摘24〜27、いずれも低)に対応。(24)`launch.sh`のロック: PID未記入は`LAUNCH_LOCK_GRACE`(既定1秒)待って再確認、古いロックの解除は`mv`で自分専用名へ退避する原子的方式(他者が取得し直した新ロックは戻して断念)、PIDが生存していてもロックが`LAUNCH_LOCK_STALE_SECONDS`(既定300秒)より古ければ古いロック扱い。(25)ロック取得直後に`is_healthy`を再確認し、成功ならロック解除・ブラウザのみ開いて終了。(26)冒頭でUTF-8ロケール(`en_US.UTF-8`優先)を`LC_ALL`に設定。(27)stamp判定の比較へ列の既定値・UNIQUEを追加(CHECK・ON UPDATE・トリガは対象外とコメント・README明記)、stamp後のupgrade失敗時は退避コピーからの復元手順を日本語エラーに含めた。単一機能に閉じた軽微な修正(reviewerの再確認は任意) | イテレーション3・段階1 |
| 3.0-stage1-r2 | 2026-09-19 | レビュー結果報告書9.7節(指摘20〜23)に対応。(20)ダイアログは失敗理由1行+ログ案内のみ表示(alembicのINFOログ抑止、詳細はログ)、表示失敗もログ記録。(22)`alembic_version`無しDBは構造が既知リビジョンと一致する場合のみ退避後にstamp→upgrade、不一致は日本語案内で停止。(21)退避コピーは一時名→リネーム。(23)`run/launch.lock`の簡易排他(古いロック自動解除)。テスト: pytest 205件(+10)・vitest 52件。単一機能に閉じた修正(起動処理)だが、詳細設計書4.7.3.1への反映が必要(差異#16) | イテレーション3・段階1 |
| 3.0-stage1-r1 | 2026-09-19 | イテレーション3・段階1のレビュー結果報告書9章(指摘14〜19)に対応。(14)`起動.app`(`launch.sh`)が起動前に`python -m app.migrate`でマイグレーションを自動適用(適用前にDBを退避コピー、既存の退避コピーは上書きせず、失敗時は日本語ダイアログで起動中止、冪等)。(15)納期を`YYYY-MM-DD`に厳格化・正規化。(16)3サービスの`project_repository`を必須化。(17)適用前後でF-07・home/summaryが一致するテストを追加。(18)型注釈・import順・README表崩れ・1章を修正、`list_due_before`は段階2で使用と明記。(19)取引先削除時の将来要件を差異#10・要確認事項#10へ明記。詳細設計書4.7.3/4.13.1の起動処理へ反映が必要(差異#13、architectへ依頼)。単一機能に閉じた修正のため、reviewerの再レビュー対象は指摘14の自動適用箇所を中心とする | イテレーション3・段階1 |
| 2.0 | 2026-09-17 | イテレーション2: 財務ダッシュボード(F-07、SC-12)を新規実装。詳細設計書2.0・基本設計書2.0・mockup(`SC-12_financial-dashboard.html`)をもとに、TDD方針(Red→Green→Refactor)で以下を実装。バックエンド: 直近12ヶ月算出の共通ユーティリティ`app/utils/date_range.py`(`build_last_12_months`/`month_start`/`month_end`)、`InvoiceRepository.aggregate_total_by_issue_month`・`PaymentRepository.aggregate_amount_by_payment_month`・`QuoteRepository.aggregate_count_and_amount_by_issue_month`/`count_in_period`/`count_converted_in_period`(既存`ExpenseRepository.aggregate_by_month`/`aggregate_by_category`はF-02と共用・無変更で再利用)、読み取り専用の`DashboardService`(発生主義での月次集計、issue_date NULLの除外、0円/0件補完、見積成約率の0除算回避)、`routers/dashboard.py`(区画ごとに独立した4本のGETエンドポイント)、レスポンススキーマ`app/schemas/dashboard.py`。既存の`Invoice.issue_date`・`Quote.issue_date`・`Payment.payment_date`にインデックスを追加し(詳細設計書6.4章)、Alembicリビジョン`2e1e85c3b7cc`を追加・適用。フロントエンド: `DashboardPage.tsx`(Recharts v3を用いた4区画のグラフ描画、区画単位で独立したTanStack Queryフックによるエラー分離表示)、`api/dashboard.ts`、`utils/format.ts`に`formatMonthLabel`/`formatLast12MonthsRangeLabel`を追加、ホーム画面(SC-01)に「財務ダッシュボード」導線カードを追加、ルーティングに`/dashboard`を追加。既存機能(F-01〜F-06)のコードはインデックス追加以外変更していない。バックエンド149件(既存127件+新規22件)・フロントエンド37件(既存30件+新規7件)のテストが全件成功、`tsc -b`・`npm run build`も成功を確認。 | イテレーション2 |
