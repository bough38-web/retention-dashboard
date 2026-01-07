import streamlit as st # Force Reload
import pandas as pd
import numpy as np
from datetime import datetime
import smtplib
from email.message import EmailMessage
import plotly.express as px
import textwrap

# Modules
from modules.config import (
    MERGED_PATH, FEEDBACK_PATH, CONTACT_PATH, 
    BRANCH_ORDER, get_smtp_config
)
from modules.data_loader import (
    load_voc_data, load_feedback, save_feedback, 
    load_contact_map, process_voc_data
)
from modules.utils import (
    sort_branch, recommend_retention_policy, filter_valid_columns
)
from modules.auth import login_form, check_login
from modules.ui import (
    inject_custom_css, force_bar_chart, force_stacked_bar, style_risk
)

# ==============================
# 1. 초기 설정 및 로그인
# ==============================
st.set_page_config(page_title="해지 VOC 종합 대시보드", layout="wide")

# Theme Injection
inject_custom_css()

# 데이터 로드 (캐싱됨)
contact_df, manager_contacts = load_contact_map(CONTACT_PATH)

# 로그인 체크
if check_login() is None:
    login_form(manager_contacts)
    st.stop()

LOGIN_TYPE = st.session_state["login_type"]
LOGIN_USER = st.session_state["login_user"]

# ==============================
# 2. 데이터 로드 및 전처리
# ==============================
df_raw = load_voc_data(MERGED_PATH)
if df_raw.empty:
    st.stop()

if "feedback_df" not in st.session_state:
    st.session_state["feedback_df"] = load_feedback(FEEDBACK_PATH)

# 데이터 가공 (VOC/Other 분리, 리스크 계산 등)
df_voc, df_other, other_union, fee_raw_col = process_voc_data(df_raw)

# 표시 컬럼 정의
fixed_order = [
    "상호", "계약번호_정제", "매칭여부", "리스크등급", "경과일수", "출처", "관리지사",
    "영업구역번호", "영업구역_통합", "구역담당자_통합", "처리자", "담당유형",
    "처리유형", "처리내용", "접수일시", "서비스개시일", "계약종료일",
    "서비스중", "서비스소", "VOC유형", "VOC유형중", "VOC유형소",
    "해지상세", "등록내용", "설치주소_표시", "시설_KTT월정료(조정)",
    "계약상태(중)", "서비스(소)"
]
display_cols_raw = [c for c in fixed_order if c in df_voc.columns]
display_cols = filter_valid_columns(display_cols_raw, df_voc)

# ==============================
# 3. 사이드바 글로벌 필터
# ==============================
# 3. 사이드바 글로벌 필터
# ==============================
# 1. 🔍 통합 검색 & 초기화
with st.sidebar:
    st.markdown("### 🔍 통합 검색")
    global_search = st.text_input("검색어 입력 (계약/상호/주소)", placeholder="Enter to search...", label_visibility="collapsed")

    if st.button("🔄 필터 초기화", key="reset_top", use_container_width=True):
        for key in list(st.session_state.keys()):
            if "filter" in key or "drill" in key: del st.session_state[key]
        st.rerun()

    st.markdown("---")

    # 2. 📅 기간 및 조직 (Period & Org)
    st.markdown("### 📅 기간 및 조직")
    
    # Date
    if "접수일시" in df_voc.columns and df_voc["접수일시"].notna().any():
        min_d = df_voc["접수일시"].min().date()
        max_d = df_voc["접수일시"].max().date()
        dr = st.date_input(
            "접수일자 범위", value=(min_d, max_d), min_value=min_d, max_value=max_d
        )
    else:
        dr = None
        st.caption("날짜 데이터 없음")

    # Branch
    branches_all = sort_branch(df_voc["관리지사"].dropna().unique())
    sel_branches = st.multiselect(
        "관리지사", options=["전체"] + branches_all, default=["전체"], key="filter_branch_btn"
    )

    # Manager (Dependent)
    if "전체" in sel_branches or not sel_branches:
        mgr_pool = sorted(df_voc["구역담당자_통합"].dropna().unique())
    else:
        mgr_pool = sorted(df_voc[df_voc["관리지사"].isin(sel_branches)]["구역담당자_통합"].dropna().unique())
    
    sel_managers = st.multiselect(
        "담당자", options=["전체"] + mgr_pool, default=["전체"], key="filter_manager_btn"
    )

    st.markdown("---")

    # 3. 🚦 상태 및 매칭 (Status)
    st.markdown("### ⚠ 리스크 등급")
    risk_all = ["HIGH", "MEDIUM", "LOW"]
    sel_risk = st.multiselect(
        "리스크 선택", options=risk_all, default=risk_all, key="filter_risk_btn", label_visibility="collapsed"
    )
    
    st.markdown("### 🔍 매칭 여부")
    match_all = ["매칭(O)", "비매칭(X)"]
    sel_match = st.multiselect(
        "매칭여부 선택", options=match_all, default=["비매칭(X)"], key="filter_match_btn", label_visibility="collapsed"
    )

    st.markdown("---")

    # 4. 💰 상세 설정 (Expander)
    with st.expander("💰 월정료 및 기타 필터", expanded=False):
        fee_bands = ["전체", "10만 이하", "10만~30만", "30만 이상"]
        sel_fee_band_radio = st.radio("월정료 구간", options=fee_bands, index=0, key="filter_fee_band_radio")
        
        fee_slider_min, fee_slider_max = st.slider(
            "월정료 범위 (만원)", 0, 100, (0, 100), step=1, key="filter_fee_band_slider"
        )

# 📂 데이터 업로드 (DB Admin Only)
with st.sidebar.expander("📂 데이터 업로드 (DB Admin Only)", expanded=False):
    up_pw = st.text_input("🔒 관리자 비밀번호", type="password", key="db_up_pw")
    if up_pw == "3867":
        uploaded_file = st.file_uploader("Excel 파일 업로드 (덮어쓰기)", type=["xlsx"])
        if uploaded_file:
            try:
                with open(MERGED_PATH, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success("업로드 및 저장 완료! 새로고침 중...")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {e}")
    elif up_pw:
        st.error("비밀번호가 올바르지 않습니다.")

# ---------------------------------------
# 필터 적용 로직
# ---------------------------------------
voc_filtered = df_voc.copy()

# 1. 권한 필터
if LOGIN_TYPE == "user":
    voc_filtered = voc_filtered[voc_filtered["구역담당자_통합"].astype(str) == LOGIN_USER]
elif LOGIN_TYPE == "branch_admin":
    branch = st.session_state.get("login_branch", "")
    voc_filtered = voc_filtered[voc_filtered["관리지사"].astype(str) == branch]

# 2. 글로벌 필터
# 2-0. 통합 검색 (Global Search)
if global_search:
    # 검색 가능 컬럼: 계약번호_정제, 상호, 설치주소_표시, 구역담당자_통합
    mask_search = (
        voc_filtered["계약번호_정제"].astype(str).str.contains(global_search, na=False) |
        voc_filtered["상호"].astype(str).str.contains(global_search, na=False) |
        voc_filtered["설치주소_표시"].astype(str).str.contains(global_search, na=False) |
        voc_filtered["구역담당자_통합"].astype(str).str.contains(global_search, na=False)
    )
    voc_filtered = voc_filtered[mask_search]

# 날짜
if dr and isinstance(dr, tuple) and len(dr) == 2:
    start_d, end_d = dr
    voc_filtered = voc_filtered[
        (voc_filtered["접수일시"] >= pd.to_datetime(start_d)) & 
        (voc_filtered["접수일시"] < pd.to_datetime(end_d) + pd.Timedelta(days=1))
    ]
# 지사
if "전체" not in sel_branches:
    voc_filtered = voc_filtered[voc_filtered["관리지사"].isin(sel_branches)]

# 담당자
if "전체" not in sel_managers:
    voc_filtered = voc_filtered[voc_filtered["구역담당자_통합"].isin(sel_managers)]
# 리스크
if sel_risk and "리스크등급" in voc_filtered.columns:
    voc_filtered = voc_filtered[voc_filtered["리스크등급"].isin(sel_risk)]

# [New] Match Filter (Save 'voc_structure' before applying Match filter for the structure chart)
voc_structure = voc_filtered.copy()

# 매칭
if sel_match and "매칭여부" in voc_filtered.columns:
    voc_filtered = voc_filtered[voc_filtered["매칭여부"].isin(sel_match)]

# 월정료
if fee_raw_col and "월정료_수치" in voc_filtered.columns:
    fs = voc_filtered["월정료_수치"].fillna(-1)
    if sel_fee_band_radio == "10만 이하": voc_filtered = voc_filtered[(fs >= 0) & (fs < 100000)]
    elif sel_fee_band_radio == "10만~30만": voc_filtered = voc_filtered[(fs >= 100000) & (fs < 300000)]
    elif sel_fee_band_radio == "30만 이상": voc_filtered = voc_filtered[fs >= 300000]
    
    start_won, end_won = fee_slider_min * 10000, fee_slider_max * 10000
    voc_filtered = voc_filtered[(fs >= start_won) & (fs <= end_won)]

unmatched_global = voc_filtered[voc_filtered["매칭여부"] == "비매칭(X)"].copy()

# ==============================
# 4. KPI 및 탭 구성
# ==============================
# Clean Landing Page (No Redundant Titles)
# Clean Landing Page (No Redundant Titles)
st.write("") # small spacer

# ----------------------------------------------------
# 💡 개념 정의 가이드 (Concept Definition)
# ----------------------------------------------------
with st.expander("❗ 개념 정의 (Definition) 보기", expanded=False):
    st.markdown(textwrap.dedent("""
    <style>
      .concept-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
        font-size: 14px;
        color: #E0E0E0; /* Light Grey Text */
        margin-bottom: 20px;
        background-color: #1E1E1E; /* Dark BG */
      }
      .concept-table th {
        background-color: #2C2F36; /* Dark Header */
        color: #FFFFFF;
        font-weight: bold;
        text-align: center;
        padding: 12px;
        border: 1px solid #444444; /* Dark Border */
      }
      .concept-table td {
        padding: 12px;
        border: 1px solid #444444;
        vertical-align: middle;
        color: #E0E0E0;
      }
      .concept-center {
        text-align: center;
      }
      .highlight-red {
        color: #FF6B6B; /* Neon Red for Dark Mode */
        font-weight: bold;
      }
      .highlight-blue {
        color: #4AA8FF; /* Neon Blue for Dark Mode */
        font-weight: bold;
      }
      .category-header {
        background-color: #262730; /* Dark Category BG */
        font-weight: bold;
        color: #FFFFFF;
      }
    </style>

    <table class="concept-table">
      <thead>
        <tr>
          <th style="width: 15%;">구분</th>
          <th style="width: 25%;">상세 상태 (Status)</th>
          <th style="width: 40%;">개념 정의 (Definition)</th>
          <th style="width: 20%;">비고 (Action)</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td rowspan="5" class="concept-center category-header">매칭<br>(Risk 관리)</td>
          <td class="concept-center highlight-red">해지</td>
          <td>서비스 계약이 완전히 종료된 상태</td>
          <td class="concept-center">재가입 유도<br>원인 분석</td>
        </tr>
        <tr>
          <td class="concept-center highlight-red">해지진행</td>
          <td>고객이 해지를 요청하여 전산상 처리가 진행 중인 단계</td>
          <td class="concept-center">해지 방어<br>(Retention)</td>
        </tr>
        <tr>
          <td class="concept-center highlight-red">정지</td>
          <td>미납, 일시정지 요청 등으로 서비스 이용이 중단된 상태</td>
          <td class="concept-center">이용 재개 유도<br>납부 안내</td>
        </tr>
        <tr>
          <td class="concept-center highlight-red">설치변경</td>
          <td>이사, 댁내 이전 등으로 장소나 장비 변경이 발생한 상태<br>(이탈 위험 존재)</td>
          <td class="concept-center">이전 설치 지원<br>약정 갱신</td>
        </tr>
        <tr>
          <td class="concept-center highlight-red">해지대응중</td>
          <td>해지 의사를 밝힌 고객에 대하여 방어 활동(상담 등)을 수행 중인 상태</td>
          <td class="concept-center">혜택 제안<br>불만 해소</td>
        </tr>
        <tr>
          <td rowspan="2" class="concept-center category-header">비매칭<br>(해지위약금/만기종료일 문의, 잠재적 이탈/ 방어활동 대상)</td>
          <td class="concept-center highlight-blue">접수 (인지)</td>
          <td>해당 시설(건)에 대해 영업사원이 인지하고 대응 중인 상태</td>
          <td class="concept-center">영업 활동 지속</td>
        </tr>
        <tr>
          <td class="concept-center highlight-blue">미접수 (미인지)</td>
          <td>해당 시설(건)이 할당되었으나, 아직 영업사원이 확인하지 않았거나 활동을 시작하지 않은 상태</td>
          <td class="concept-center">신속한 접수/해지방어 처리 대상</td>
        </tr>
      </tbody>
    </table>
    """), unsafe_allow_html=True)


# ----------------------------------------------------
# 📊 매칭/비매칭 현황 (Structure Analysis) - MOVED HERE
# ----------------------------------------------------
with st.expander("매칭/비매칭 현황! (전체 구조 분석)", expanded=True):
    # Use 'voc_structure' which ignores the 'Match' filter but keeps others (Date, Branch, etc.)
    if "매칭여부" in voc_structure.columns:
        # Simplify Layout: Pie [1.2], Bar [2.0] (Full Width)
        c_struc_1, c_struc_2 = st.columns([1.2, 2.0], gap="small")
        
        with c_struc_1:
            with st.container(border=True):
                # Total Ratio
                tot_struc = voc_structure["매칭여부"].value_counts().reset_index()
                tot_struc.columns = ["매칭여부", "count"]
                
                fig_pie_struc = px.pie(
                    tot_struc, values="count", names="매칭여부", 
                    hole=0.4,
                    color="매칭여부",
                    color_discrete_map={"매칭(O)": "#00CC96", "비매칭(X)": "#EF553B"}
                )
                fig_pie_struc.update_traces(textposition='inside', textinfo='percent+label')
                
                # Layout: Transparent BG (Container handles the border/bg)
                fig_pie_struc.update_layout(
                    title=dict(text="<b>🍰 전체 비율</b>", x=0.5, xanchor='center', font=dict(size=18, color="#FFFFFF")),
                    height=320, 
                    autosize=True,
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=12, color="#FAFAFA")),
                    plot_bgcolor="rgba(0,0,0,0)", 
                    paper_bgcolor="rgba(0,0,0,0)", 
                    margin=dict(t=60, b=20, l=10, r=10),
                    font=dict(family="Noto Sans KR", size=14, color="#FAFAFA")
                )
                st.plotly_chart(fig_pie_struc, use_container_width=True, config={'displayModeBar': False})

        with c_struc_2:
            with st.container(border=True):
                # Group by Branch x Match
                grp_struc = voc_structure.groupby(["관리지사", "매칭여부"])["계약번호_정제"].nunique().reset_index(name="계약수")
                
                # Explicit Ordering
                grp_struc["관리지사"] = pd.Categorical(grp_struc["관리지사"], categories=BRANCH_ORDER, ordered=True)
                grp_struc = grp_struc.sort_values("관리지사")
                
                fig_struc = px.bar(
                    grp_struc, x="관리지사", y="계약수", color="매칭여부",
                    text="계약수",
                    color_discrete_map={"매칭(O)": "#00CC96", "비매칭(X)": "#EF553B"},
                    category_orders={"관리지사": BRANCH_ORDER}
                )
                
                # Layout: Transparent BG
                fig_struc.update_layout(
                    title=dict(text="<b>🏢 지사별 매칭/비매칭 분포</b>", x=0.5, xanchor='center', font=dict(size=18, color="#FFFFFF")),
                    height=320, 
                    autosize=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, title="", font=dict(size=12, color="#FAFAFA")),
                    plot_bgcolor="rgba(0,0,0,0)", 
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=60, b=20, l=20, r=20),
                    xaxis=dict(title=None, tickfont=dict(size=12, color="#FAFAFA")),
                    yaxis=dict(title=None, showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
                    font=dict(family="Noto Sans KR", size=14, color="#FAFAFA")
                )
                st.plotly_chart(fig_struc, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("데이터 확인 필요")

st.markdown("---")

k1, k2, k3, k4 = st.columns(4)
k1.metric("VOC 접수", f"{len(voc_filtered):,}")
k2.metric("유니크 계약", f"{voc_filtered['계약번호_정제'].nunique():,}")
k3.metric("비매칭(X)", f"{unmatched_global['계약번호_정제'].nunique():,}")
k4.metric("매칭(O)", f"{voc_filtered[voc_filtered['매칭여부'] == '매칭(O)']['계약번호_정제'].nunique():,}")

st.markdown("---")

tab_viz, tab_all, tab_unmatched, tab_drill, tab_filter, tab_alert, tab_branch_admin_report = st.tabs([
    "📊 지사/담당자 시각화", "📘 VOC 전체(계약 기준)", "🧯 해지방어 활동시설(비매칭)",
    "🔍 해지상담대상 활동등록", "🎯 정밀 필터", "📨 담당자 알림", "🏢 지사 관리자 전용"
])

# ----------------------------------------------------
# TAB VIZ
# ----------------------------------------------------
with tab_viz:
    viz_base = unmatched_global.copy()
    st.subheader("📊 지사 / 담당자별 비매칭 리스크 현황")
    
    if viz_base.empty:
        st.info("데이터가 없습니다.")
    else:
        # Local Filters
        colA, colB = st.columns(2)
        bz_opts = ["전체"] + sort_branch(viz_base["관리지사"].dropna().unique())
        sel_bz = colA.selectbox("🏢 지사 선택", bz_opts, key="viz_bz")
        
        tmp = viz_base[viz_base["관리지사"] == sel_bz] if sel_bz != "전체" else viz_base
        mgr_opts = ["전체"] + sorted(tmp["구역담당자_통합"].dropna().astype(str).unique())
        sel_mg = colB.selectbox("👤 담당자 선택", mgr_opts, key="viz_mg")
        
        # Apply Filter
        if sel_bz != "전체": viz_base = viz_base[viz_base["관리지사"] == sel_bz]
        if sel_mg != "전체": viz_base = viz_base[viz_base["구역담당자_통합"].astype(str) == sel_mg]
        
        st.success(f"📌 필터 적용된 계약 수: {viz_base['계약번호_정제'].nunique():,} 건")
        
        # Charts
        st.markdown("### 🧱 지사별 비매칭 계약수 (리스크 적층)")
        grp_bz = viz_base.groupby(["관리지사", "리스크등급"])["계약번호_정제"].nunique().reset_index(name="계약수")
        piv_bz = grp_bz.pivot(index="관리지사", columns="리스크등급", values="계약수").fillna(0).reset_index()
        
        # Explicit Sort by Custom Branch Order
        piv_bz["관리지사"] = pd.Categorical(piv_bz["관리지사"], categories=BRANCH_ORDER, ordered=True)
        piv_bz = piv_bz.sort_values("관리지사")
        
        force_stacked_bar(piv_bz, "관리지사", [c for c in ["HIGH","MEDIUM","LOW"] if c in piv_bz.columns])
        
        st.markdown("### 👤 담당자별 TOP 15 (유니크 계약 · 리스크 적층)")
        grp_mg = viz_base.groupby(["구역담당자_통합", "리스크등급"])["계약번호_정제"].nunique().reset_index(name="계약수")
        piv_mg = grp_mg.pivot(index="구역담당자_통합", columns="리스크등급", values="계약수").fillna(0)
        piv_mg["Total"] = piv_mg.sum(axis=1)
        piv_mg = piv_mg.sort_values("Total", ascending=False).head(15).drop(columns=["Total"]).reset_index()
        force_stacked_bar(piv_mg, "구역담당자_통합", [c for c in ["HIGH","MEDIUM","LOW"] if c in piv_mg.columns])
        
        st.markdown("---")
        st.markdown("### ⏳ 경과일수(평균) 분석")
        
        row_days_1, row_days_2 = st.columns(2)
        
        with row_days_1:
            st.markdown("#### 🏢 지사별 평균 경과일수")
            if "경과일수" in viz_base.columns:
                grp_days_bz = viz_base.groupby("관리지사")["경과일수"].mean().reset_index()
                # Explicit Sort by Custom Branch Order
                grp_days_bz["관리지사"] = pd.Categorical(grp_days_bz["관리지사"], categories=BRANCH_ORDER, ordered=True)
                grp_days_bz = grp_days_bz.sort_values("관리지사")
                
                fig_days_bz = px.bar(
                    grp_days_bz, 
                    x="관리지사", 
                    y="경과일수",
                    text="경과일수",
                    color="관리지사", # optional: distinct colors
                    category_orders={"관리지사": BRANCH_ORDER}
                )
                fig_days_bz.update_traces(texttemplate='%{text:.1f}일', textposition='outside')
                fig_days_bz.update_layout(height=400)
                st.plotly_chart(fig_days_bz, use_container_width=True)
            else:
                st.info("경과일수 데이터가 없습니다.")

        with row_days_2:
            st.markdown("#### 👤 담당자별 평균 경과일수 (Top 15)")
            if "경과일수" in viz_base.columns:
                # Group by Manager
                grp_days_mg = viz_base.groupby("구역담당자_통합")["경과일수"].mean().reset_index()
                grp_days_mg = grp_days_mg.sort_values("경과일수", ascending=False).head(15)
                
                fig_days_mg = px.bar(
                    grp_days_mg, 
                    x="구역담당자_통합", 
                    y="경과일수",
                    text="경과일수",
                    color="구역담당자_통합",
                )
                fig_days_mg.update_traces(texttemplate='%{text:.1f}일', textposition='outside')
                fig_days_mg.update_layout(height=400)
                st.plotly_chart(fig_days_mg, use_container_width=True)
            else:
                st.info("경과일수 데이터가 없습니다.")

        st.markdown("---")
        st.markdown("### 📉 심화 분석 (분포/추이/히트맵)")
        
        tab_box, tab_trend, tab_hm = st.tabs(["📦 분포 (Boxplot)", "📈 일별 추이", "🗺️ 지사x담당 히트맵"])
        
        # 1. Boxplots
        with tab_box:
            b1, b2 = st.columns(2)
            with b1:
                st.markdown("##### 🏢 지사별 경과일수 분포")
                if "경과일수" in viz_base.columns:
                    fig_box_bz = px.box(
                        viz_base, x="관리지사", y="경과일수", color="관리지사",
                        points="outliers", # show only outliers to reduce noise, or "all"
                        category_orders={"관리지사": BRANCH_ORDER}
                    )
                    fig_box_bz.update_layout(height=400, showlegend=False)
                    st.plotly_chart(fig_box_bz, use_container_width=True)
            
            with b2:
                st.markdown("##### 👤 담당자별 경과일수 분포 (Top 20)")
                if "경과일수" in viz_base.columns:
                    # Filter Top 20 Managers by count
                    top_mgrs = viz_base["구역담당자_통합"].value_counts().head(20).index
                    df_box_mg = viz_base[viz_base["구역담당자_통합"].isin(top_mgrs)]
                    
                    fig_box_mg = px.box(
                        df_box_mg, x="구역담당자_통합", y="경과일수", color="구역담당자_통합"
                    )
                    fig_box_mg.update_layout(height=400, showlegend=False)
                    st.plotly_chart(fig_box_mg, use_container_width=True)

        # 2. Daily Trend
        with tab_trend:
            st.markdown("##### 📅 일별 비매칭 접수 추이")
            if "접수일시" in viz_base.columns:
                # Group by Date
                trend_base = viz_base.copy()
                trend_base["접수일자"] = trend_base["접수일시"].dt.date
                grp_trend = trend_base.groupby("접수일자")["계약번호_정제"].nunique().reset_index(name="접수건수")
                
                fig_trend = px.line(
                    grp_trend, x="접수일자", y="접수건수", markers=True,
                    title="일별 비매칭 발생 건수"
                )
                fig_trend.update_layout(height=400)
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("접수일시 데이터가 없습니다.")

        # 3. Heatmap
        with tab_hm:
            st.markdown("##### 🗺️ 지사 vs 담당자 비매칭 건수 히트맵")
            # Pivot: Branch(X) x Manager(Y) -> Count
            hm_grp = viz_base.groupby(["관리지사", "구역담당자_통합"])["계약번호_정제"].nunique().reset_index(name="건수")
            if not hm_grp.empty:
                fig_hm = px.density_heatmap(
                    hm_grp, x="관리지사", y="구역담당자_통합", z="건수",
                    nbinsx=20, nbinsy=20, color_continuous_scale="Viridis",
                    text_auto=True,
                    category_orders={"관리지사": BRANCH_ORDER}
                )
                fig_hm.update_layout(height=600)
                st.plotly_chart(fig_hm, use_container_width=True)
            else:
                st.info("데이터가 부족하여 히트맵을 생성할 수 없습니다.")

# ----------------------------------------------------
# TAB ALL (VOC 전체)
# ----------------------------------------------------
with tab_all:
    st.subheader("📘 VOC 전체 리스트 (계약 기준)")
    st.caption(f"총 {len(voc_filtered):,} 건 (필터 적용됨)")
    
    if voc_filtered.empty:
        st.info("조건에 맞는 데이터가 없습니다.")
    else:
        # Display Columns Logic
        view_cols = [c for c in display_cols if c in voc_filtered.columns]
        st.dataframe(
            style_risk(voc_filtered[view_cols]), 
            use_container_width=True, 
            height=600,
            hide_index=True
        )

# ----------------------------------------------------
# TAB UNMATCHED (비매칭)
# ----------------------------------------------------
with tab_unmatched:
    st.subheader("🧯 해지방어 활동시설 (비매칭 건)")
    st.caption(f"총 {len(unmatched_global):,} 건 (비매칭 & 필터 적용됨)")
    
    if unmatched_global.empty:
        st.info("비매칭 데이터가 없습니다.")
    else:
        view_cols_u = [c for c in display_cols if c in unmatched_global.columns]
        st.dataframe(
            style_risk(unmatched_global[view_cols_u]), 
            use_container_width=True, 
            height=600
        )

with tab_drill:
    st.subheader("🔍 해지상담대상 활동등록")
    
    # Simple search interface
    d1, d2 = st.columns(2)
    s_cn = d1.text_input("계약번호 검색", key="drill_cn")
    
    drill_df = voc_filtered.copy()
    if s_cn:
        drill_df = drill_df[drill_df["계약번호_정제"].astype(str).str.contains(s_cn)]
    
    if drill_df.empty:
        st.info("검색 결과가 없습니다.")
    else:
        # Contract Select with Detailed Info
        # Format: [Branch] Manager | Contract | Company
        drill_df["display_opt"] = (
            "[" + drill_df["관리지사"].astype(str) + "] " +
            drill_df["구역담당자_통합"].astype(str) + " | " + 
            drill_df["계약번호_정제"].astype(str) + " | " + 
            drill_df["상호"].astype(str)
        )
        
        # Mapping: Display Label -> Contract ID
        label_map = dict(zip(drill_df["display_opt"], drill_df["계약번호_정제"]))
        
        sel_label = st.selectbox("계약 선택 (지사|담당|계약|상호)", options=drill_df["display_opt"].unique(), key="drill_sel")
        
        sel_cn_drill = label_map.get(sel_label)
        
        if sel_cn_drill:
            row_info = df_voc[df_voc["계약번호_정제"] == sel_cn_drill].iloc[0]
            
            # Recommendation
            st.markdown("### 🤖 방어 정책 추천")
            rec = recommend_retention_policy(row_info)
            st.success(f"추천: {rec['primary_action']}")
            st.info(f"대안: {rec['backup_action']}")
            st.caption(f"가이드: {rec['comment']}")
            
            # Feedback Form
            st.markdown("### 📝 활동 내역")
            fb_df = st.session_state["feedback_df"]
            fb_curr = fb_df[fb_df["계약번호_정제"].astype(str) == str(sel_cn_drill)]
            
            if not fb_curr.empty:
                st.dataframe(fb_curr[["등록일자","등록자","고객대응내용"]])
            
            with st.form("fb_form"):
                content = st.text_area("활동내용")
                if st.form_submit_button("등록"):
                    new_row = {
                        "계약번호_정제": sel_cn_drill,
                        "고객대응내용": content,
                        "등록자": LOGIN_USER,
                        "등록일자": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "비고": ""
                    }
                    st.session_state["feedback_df"] = pd.concat([fb_df, pd.DataFrame([new_row])], ignore_index=True)
                    save_feedback(FEEDBACK_PATH, st.session_state["feedback_df"])
                    st.success("등록되었습니다.")
                    st.rerun()

# ----------------------------------------------------
# TAB ALERT (Email)
# ----------------------------------------------------
with tab_alert:
    st.subheader("📨 담당자 알림 발송")
    if contact_df.empty:
        st.error("담당자 매핑 파일이 없습니다.")
    else:
        # Alert Logic
        um_alert = unmatched_global.copy()
        mgrs = sorted(um_alert["구역담당자_통합"].dropna().unique())
        sel_alert_mgr = st.selectbox("담당자 선택", ["(선택)"] + mgrs)
        
        if sel_alert_mgr != "(선택)":
            info = manager_contacts.get(sel_alert_mgr, {})
            email_addr = st.text_input("이메일", value=info.get("email",""))
            
            target_rows = um_alert[um_alert["구역담당자_통합"] == sel_alert_mgr]
            st.write(f"대상: {len(target_rows)} 건")
            st.dataframe(target_rows[["계약번호_정제","상호","리스크등급"]].head())
            
            if st.button("이메일 발송"):
                smtp_conf = get_smtp_config()
                # Basic validation
                if not email_addr or not smtp_conf["HOST"]:
                    st.error("이메일 또는 SMTP 설정이 부족합니다.")
                else:
                    try:
                        # -------------------------
                        # Generate HTML Summary
                        # -------------------------
                        summary_html = """
                        <html>
                        <body style="font-family: Arial, sans-serif;">
                            <h2>[해지VOC] 비매칭 건 알림</h2>
                            <p>담당자님, 안녕하세요.<br>
                            시스템에 등록되지 않은 해지 VOC 비매칭 건이 확인되어 공유드립니다.</p>
                            
                            <p><b>대상 건수:</b> {count} 건</p>
                            
                            <table border="1" style="border-collapse: collapse; width: 100%; max-width: 800px; font-size: 12px;">
                                <tr style="background-color: #f2f2f2;">
                                    <th style="padding: 8px;">계약번호</th>
                                    <th style="padding: 8px;">상호</th>
                                    <th style="padding: 8px;">리스크등급</th>
                                    <th style="padding: 8px;">관리지사</th>
                                </tr>
                                {rows}
                            </table>
                            
                            <p><br>자세한 내용은 첨부된 CSV 파일을 확인해주시기 바랍니다.<br>
                            감사합니다.</p>
                        </body>
                        </html>
                        """
                        
                        # Create rows for the table (limit to top 20 to preserve email size)
                        table_rows = ""
                        for _, row in target_rows.head(20).iterrows():
                            # Risk styling logic for email
                            risk = str(row.get("리스크등급", ""))
                            bg_color = "#ffffff"
                            if risk == "HIGH": bg_color = "#ffe6e6"
                            elif risk == "MEDIUM": bg_color = "#fffde7"
                            
                            table_rows += f"""
                            <tr style="background-color: {bg_color};">
                                <td style="padding: 8px;">{row.get('계약번호_정제', '')}</td>
                                <td style="padding: 8px;">{row.get('상호', '')}</td>
                                <td style="padding: 8px;">{risk}</td>
                                <td style="padding: 8px;">{row.get('관리지사', '')}</td>
                            </tr>
                            """
                        
                        if len(target_rows) > 20:
                            table_rows += "<tr><td colspan='4' style='padding:8px; text-align:center;'>... (전체 데이터는 첨부파일 확인) ...</td></tr>"

                        final_body = summary_html.format(count=len(target_rows), rows=table_rows)

                        msg = EmailMessage()
                        msg["Subject"] = f"[VOC] {sel_alert_mgr}님 비매칭 건 알림"
                        msg["From"] = f"{smtp_conf['SENDER_NAME']} <{smtp_conf['USER']}>"
                        msg["To"] = email_addr
                        msg.set_content(f"{len(target_rows)}건의 비매칭 건이 있습니다. (HTML 지원 필요)") # Fallback
                        msg.add_alternative(final_body, subtype='html')
                        
                        # Attachment
                        csv_data = target_rows.to_csv(index=False).encode("utf-8-sig")
                        msg.add_attachment(csv_data, maintype="application", subtype="octet-stream", filename="data.csv")
                        
                        with smtplib.SMTP(smtp_conf["HOST"], smtp_conf["PORT"]) as server:
                            server.starttls()
                            if smtp_conf["USER"] and smtp_conf["PASSWORD"]:
                                server.login(smtp_conf["USER"], smtp_conf["PASSWORD"])
                            server.send_message(msg)
                        st.success(f"{email_addr} 로 발송 성공")
                    except Exception as e:
                        st.error(f"발송 실패: {e}")

# ----------------------------------------------------
# TAB BRANCH ADMIN
# ----------------------------------------------------
with tab_branch_admin_report:
    if LOGIN_TYPE == "branch_admin":
        st.subheader(f"🏢 {st.session_state['login_branch']} 관리자 리포트")
        # .. reporting logic ..
    else:
        st.info("권한이 없습니다.")

