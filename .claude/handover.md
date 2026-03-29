# Handover: arkiv Tauri App — JS 不執行修復

## Goal
修復 arkiv Media Asset Manager 的 Tauri 桌面 app — 素材不顯示、功能失效。

## Completed
- **Bisect 完成**: 從 `ee72c11` 開始，5 個 commit agent teams 平行分析
- **server.py 快取修復**: 移除 `_INDEX_HTML` 快取，改為每次讀取 index.html (`~/.arkiv/server.py` line 558-570)
- **Python 3.9 相容**: `str | None` → `Optional[str]` (server.py)
- **DOMContentLoaded 包裝**: event listeners + init 移到 DOMContentLoaded callback (index.html line 878+)
- **CSP 放寬測試**: 改為 `default-src * 'unsafe-inline' 'unsafe-eval' data: blob:` — 無效
- **跨瀏覽器測試**: Chrome ✅ Safari ✅ Tauri ❌
- **`withGlobalTauri` 移除測試**: 最後一次嘗試，結果待確認

## Pending (優先順序)
1. ~~確認 `withGlobalTauri` 移除~~ — 已測，仍失敗。排除 Tauri injection 問題。
2. **用 Safari WebView Inspector 調試** — `WEBKIT_INSPECTOR=1 cargo tauri dev`，然後 Safari > Develop > 選 WebView > Console 看具體 error
3. **恢復 Tauri native 功能** — 如果 `withGlobalTauri` 確認有問題，改用 `@tauri-apps/api` npm 模組方式引入 Tauri API，而非 global injection
4. **測試 Import ("+" 按鈕)** — 需要 `window.__TAURI__.dialog` 支援
5. **清理** — commit 修復到 main

## Blocked / Notes
- **核心矛盾**: 包 try-catch 時 Tauri 正常顯示 8 筆素材，移除 try-catch 就空白。但 Chrome/Safari 不包 try-catch 也正常。
- **可能的 root cause**: Tauri 的 `withGlobalTauri` 注入一段 JS bridge（定義 `window.__TAURI__`），這段注入 script 可能修改了全域環境（類似 SES lockdown），導致後續 inline script 的某些操作失敗
- **Safari 的 Develop menu 已開啟** — 可用 Safari > Develop > 選 WebView 來看 Tauri WebView 的 console

## Key Files
- `~/.arkiv/index.html` — 前端 SPA（已加 DOMContentLoaded 包裝）
- `~/.arkiv/server.py` — FastAPI backend（已修：不快取 HTML、Optional[str]）
- `~/.arkiv/src-tauri/tauri.conf.json` — Tauri config（CSP 已放寬、withGlobalTauri 已移除）
- `~/.arkiv/src-tauri/src/main.rs` — Tauri plugins（opener + dialog）
- `~/.arkiv/db.py` — SQLite DB 層

## Environment Context
- **Backend**: `python3 -m uvicorn server:app --host 0.0.0.0 --port 8501`（需手動啟動）
- **Tauri**: `cd ~/.arkiv && cargo tauri dev`
- **Python**: 3.9（系統版，不支援 `str | None` 語法）
- **Cargo tauri CLI**: 2.10.1
- **DB**: `~/.arkiv/media.db`（SQLite，已有 8 筆素材）
- **Thumbnails**: `~/.arkiv/thumbnails/`（部分 404）

## Suggested Next Commands
```bash
# 1. 啟動 backend
cd ~/.arkiv && python3 -m uvicorn server:app --host 0.0.0.0 --port 8501 &

# 2. 用 Safari WebView inspector 調試 Tauri
WEBKIT_INSPECTOR=1 cargo tauri dev
# 然後 Safari > Develop > 選擇 arkiv WebView > Console

# 3. 或直接跑 Tauri 看目前狀態
cargo tauri dev
```

## Session Log
- 2026-03-30 00:30 — CLI session 結束，handover to Cowork
