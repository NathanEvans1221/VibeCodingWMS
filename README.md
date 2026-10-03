# VibeCodingWMS - 倉儲管理系統

![WMS01](./images/WMS01.jpg)

這是一個基於 Flask 的倉儲管理系統（WMS），用於展示基本的倉儲管理功能。

## 功能特色

- 商品與儲位管理
- 入庫與出庫作業
- 庫存查詢與盤點
- 簡潔的網頁介面

## 安裝與執行

1. 安裝依賴套件：
```bash
pip install -r requirements.txt
```

2. 執行應用程式：
```bash
python app.py
```

3. 開啟瀏覽器訪問：http://localhost:5000

停止服務時，回到執行中的終端機按 `Ctrl+C`。

### 執行設定

- JSON 資料固定儲存在專案 `data` 目錄，不受目前終端機所在路徑影響。
- Flask Secret Key 預設於啟動時隨機產生。需要跨重啟維持 session 時，請設定 `FLASK_SECRET_KEY` 環境變數。
- Debug 預設關閉；本機除錯時可設定 `FLASK_DEBUG=1` 後啟動。

## 技術架構

- 後端：Python Flask
- 前端：Jinja2 Templates + Bootstrap
- 資料儲存：記憶體資料結構 + JSON 檔案
