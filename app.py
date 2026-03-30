import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="CH 工時追蹤器", layout="wide", page_icon="📊")
st.title("📊 週報 CH 工時追蹤器")
st.caption("填寫後自動儲存，全體資料即時顯示 • 同用戶自動覆蓋")

# ==================== Google Sheets 設定 ====================
@st.cache_resource
def connect_gsheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(creds)
    # ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
    # 請把下面這行改成你的 Google Sheet ID（URL 中 /d/ 後面的那一串）
    sh = gc.open_by_key("1wH-tM_W3d24Yj0CF5zbA9S8ID9vFX_Nv2mf2codVxK8")
    return sh.worksheet("Sheet1")

worksheet = connect_gsheet()

# 欄位定義
COLUMNS = ["Name", "Total_CH_Hrs_this_week", "Avg_CH_per_actual_working_day",
           "Public_holidays", "Annual_leave_Business_trip_days", "Non_chargeable_projects_tasks", "Timestamp"]

def load_data():
    try:
        records = worksheet.get_all_records()
        if not records:
            return pd.DataFrame(columns=COLUMNS)
        df = pd.DataFrame(records)
        # 確保欄位順序
        return df[COLUMNS]
    except:
        return pd.DataFrame(columns=COLUMNS)

# ==================== 表單 ====================
st.subheader("✍️ 填寫本週資料")
with st.form("ch_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        user = st.text_input("👤 你的姓名 / 員工編號 / Email（必填）", placeholder="e.g. sugar@company.com")
        total_ch = st.number_input("Total CH Hrs this week", min_value=0.0, step=0.5, format="%.1f")
        avg_ch = st.number_input("Average CH Hrs per actual working day this week", min_value=0.0, step=0.5, format="%.1f")
    with col2:
        public_holidays = st.number_input("Public holidays（天數）", min_value=0, step=1)
        leave_days = st.number_input("Annual leave / Business trip（天數）", min_value=0.0, step=0.5, format="%.1f")
    
    non_chargeable = st.text_area("Non-chargeable projects/tasks", placeholder="請列出非計費項目或任務（可多行）")
    
    submitted = st.form_submit_button("✅ 送出（自動覆蓋舊資料）", type="primary", use_container_width=True)

if submitted:
        if not user.strip():
            st.error("❌ 請填寫你的用戶識別資訊（姓名 / Email / 員工編號）")
            st.stop()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 處理多行文字，防止 JSON 錯誤
        non_chargeable_clean = (non_chargeable or "").strip().replace("\n", "\\n")
        
        new_row = {
            "User": user.strip(),
            "Timestamp": timestamp,
            "Total_CH_Hrs_this_week": float(total_ch),
            "Avg_CH_per_actual_working_day": float(avg_ch),
            "Public_holidays": int(public_holidays),
            "Annual_leave_Business_trip_days": float(leave_days),
            "Non_chargeable_projects_tasks": non_chargeable_clean
        }
        
        # 讀取現有資料並移除該用戶的舊紀錄
        df = load_data()
        if not df.empty:
            df = df[df["User"] != user.strip()]
        
        # 新增新資料
        new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
        # === 安全更新：先寫標題 + 資料，防止標題消失 ===
        worksheet.clear()  # 清空內容
        
        # 確保標題永遠在第一行
        header = new_df.columns.tolist()
        values = [header] + new_df.values.tolist()
        
        # 使用 RAW 模式更新整個工作表
        worksheet.update(values, value_input_option="RAW")
        
        st.success(f"🎉 {user.strip()} 的資料已成功儲存！舊資料已自動覆蓋。")
        st.rerun()

# ==================== 顯示全體表格 ====================
st.subheader("📋 全體用戶最新資料")
df = load_data()
if df.empty:
    st.info("目前還沒有任何資料，快來填寫第一筆吧！")
else:
    # 排序：最新提交在最上面
    df = df.sort_values(by="Timestamp", ascending=False)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Timestamp": st.column_config.DatetimeColumn("更新時間", format="YYYY-MM-DD HH:mm"),
            "Total_CH_Hrs_this_week": st.column_config.NumberColumn("Total CH Hrs", format="%.1f"),
            "Avg_CH_per_actual_working_day": st.column_config.NumberColumn("Avg CH / day", format="%.1f"),
        }
    )
    
    # 下載按鈕
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("💾 下載 CSV", csv, "ch_hours_all_users.csv", "text/csv", use_container_width=True)

st.caption("💡 小提示：同一個用戶再次填寫時，系統會自動找到舊資料並替換，整個表格永遠只保留最新一筆。")
