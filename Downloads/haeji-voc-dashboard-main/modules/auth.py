import streamlit as st
from modules.config import get_admin_password, get_branch_admin_passwords

def _inject_kt_security_css():
    st.markdown("""
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap" rel="stylesheet">
        <style>
            /* 🚫 Hide Sidebar & Header */
            [data-testid="stSidebar"], section[data-testid="stSidebar"] { display: none !important; }
            header { display: none !important; }
            
            /* 🏳️ Global Settings */
            .stApp {
                background-color: #F3F4F6 !important; /* Tailwind gray-100 */
                font-family: 'Noto Sans KR', sans-serif !important;
                color: #1F2937 !important;
            }
            .stApp * {
                color: #1F2937 !important; /* FORCE DARK TEXT EVERYWHERE */
            }
            .block-container { 
                padding: 1rem !important; 
                max-width: 100% !important; 
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                justify-content: center !important;
                min-height: 100vh !important;
            }

            /* 🧱 Layout Containers */
            .login-wrapper {
                width: 100%;
                max-width: 1024px;
                background: white;
                border-radius: 1rem;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
                display: flex;
                flex-direction: row;
                overflow: hidden;
            }
            
            /* Column Override for Split Layout */
            div[data-testid="stHorizontalBlock"] {
                width: 100% !important;
                max-width: 1000px !important;
                min-width: 320px !important;
                background-color: #FFFFFF !important;
                border-radius: 1rem !important;
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04) !important;
                overflow: hidden !important;
                gap: 0 !important;
                margin: auto !important; /* Key fix */
                align-self: center !important;
                display: flex !important;
                flex-direction: row !important;
            }
            
            /* Left Column (Brand) */
            div[data-testid="column"]:nth-of-type(1) {
                background-color: #F9FAFB; /* gray-50 */
                position: relative;
                padding: 0 !important;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 550px;
            }
            /* Gradient Overlay equivalent */
            div[data-testid="column"]:nth-of-type(1)::before {
                content: "";
                position: absolute;
                inset: 0;
                background: linear-gradient(to bottom right, #f3f4f6, #e5e7eb);
                opacity: 0.5;
                z-index: 0;
            }

            /* Right Column (Form) */
            div[data-testid="column"]:nth-of-type(2) {
                background-color: #FFFFFF;
                padding: 3rem !important;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }

            /* ✒️ Typography & Elements */
            .brand-header {
                font-size: 1.875rem; 
                font-weight: 700;
                color: #1F2937; /* gray-800 */
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 2rem;
            }
            .text-kt-red { color: #E60012; }
            
            h2.form-title {
                font-size: 1.5rem;
                font-weight: 700;
                color: #111827; /* gray-900 */
                margin-bottom: 0.25rem;
            }
            p.form-desc {
                font-size: 0.875rem;
                color: #6B7280; /* gray-500 */
                margin-bottom: 2rem;
            }

            /* 🎨 Input Styling (Targeting Streamlit widgets) */
            .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
                background-color: #F9FAFB !important; /* gray-50 */
                border: 1px solid #E5E7EB !important; /* gray-200 */
                border-radius: 0.5rem !important;
                padding: 1rem !important;
                color: #374151 !important;
                font-size: 1rem !important;
                box-shadow: none !important;
            }
            .stTextInput input:focus, .stSelectbox div[data-baseweb="select"] > div:focus-within {
                border-color: #E60012 !important;
                box-shadow: 0 0 0 3px rgba(230, 0, 18, 0.1) !important;
            }
            /* Remove Input Labels visually if we want placeholder-only feel, 
               but Streamlit labels are good for accessibility. We'll keep them subtle or hide if redundancy. 
               The design request has icons inside input, Streamlit doesn't support that easily. 
               We will stick to standard Streamlit inputs matching the style. */
            .stTextInput label {
                display: none;
            }
            
            /* 🔴 Button */
            .stButton > button {
                width: 100%;
                background-color: #E60012 !important;
                color: white !important;
                font-weight: 700 !important;
                border-radius: 0.5rem !important;
                padding: 0.8rem !important;
                border: none !important;
                margin-top: 1rem;
                box-shadow: 0 10px 15px -3px rgba(254, 202, 202, 0.5); /* shadow-red-200 */
                transition: transform 0.1s;
            }
            .stButton > button:hover {
                background-color: #C4000F !important;
                transform: scale(1.01);
            }

            /* Tabs - Custom Pill Style */
            .stTabs [data-baseweb="tab-list"] {
                border-bottom: 1px solid #E5E7EB;
                gap: 1rem;
                margin-bottom: 2rem;
                justify-content: center; /* Center Tabs */
            }
            .stTabs [data-baseweb="tab"] {
                padding: 0.5rem 1rem !important;
                color: #6B7280 !important;
                border-radius: 0.5rem !important;
                border: 1px solid transparent !important;
                transition: all 0.2s;
            }
            /* Active Tab: Dark Blue Bg, White Text */
            .stTabs [aria-selected="true"] {
                background-color: #1A5CC7 !important; /* Dark Blue */
                color: #FFFFFF !important; /* White Text */
                border: none !important;
                box-shadow: 0 4px 6px -1px rgba(26, 92, 199, 0.3);
            }
            /* Force Text Color Inside Active Tab */
            .stTabs [aria-selected="true"] p, 
            .stTabs [aria-selected="true"] span,
            .stTabs [aria-selected="true"] div {
                color: #FFFFFF !important;
            }

            /* Footer Grid */
            .grid-links {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 0.75rem;
                margin-top: 1.5rem;
            }
            .grid-btn {
                padding: 0.5rem;
                border: 1px solid #E5E7EB;
                border-radius: 0.25rem;
                font-size: 0.875rem;
                color: #4B5563;
                text-align: center;
                background: white;
            }

            /* Bottom Info */
            .bottom-info {
                margin-top: 2rem;
                max-width: 1024px;
                display: flex;
                gap: 0.75rem;
                color: #6B7280;
                font-size: 0.875rem;
            }
            
            /* Hide Streamlit Elements */
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

def login_form(manager_contacts: dict):
    _inject_kt_security_css()
    
    # Global Header (Outside Card) - REMOVED

    # Split Layout
    left_col, right_col = st.columns([1, 1])
    
    # === Left Panel (Brand) ===
    with left_col:
        st.markdown("""
            <div style="position: relative; z-index: 10; text-align: center; padding: 2rem;">
                <div style="width: 12rem; height: 12rem; margin: 0 auto 1.5rem auto; background: white; border-radius: 9999px; display: flex; align-items: center; justify-content: center; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); position: relative;">
                    <!-- Pulse Effect Ring -->
                    <div style="position: absolute; inset: 0; border-radius: 9999px; border: 1px solid #F3F4F6;"></div>
                    <!-- Shield Icon (SVG) -->
                    <svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#E60012" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                        <path d="m9 12 2 2 4-4"/>
                    </svg>
                </div>
                <h3 style="font-size: 1.5rem; font-weight: 700; color: #1F2937; margin-bottom: 0.5rem;">해지방어 관리 솔루션</h3>
                <div style="position: absolute; bottom: -3rem; left: 0; width: 100%; height: 0.5rem; background: #E60012;"></div>
            </div>
        """, unsafe_allow_html=True)
        
    # === Right Panel (Form) ===
    with right_col:
        st.markdown('<h2 class="form-title">시스템 로그인</h2>', unsafe_allow_html=True)
        st.markdown('<p class="form-desc">권한에 맞는 계정 유형을 선택해주세요.</p>', unsafe_allow_html=True)
        
        # Tabs (Renamed Active)
        tab_admin, tab_user, tab_branch = st.tabs(["관리자", "구역담당", "지사담당"])
        
        with tab_admin:
            st.write("")
            pw = st.text_input("admin_pw_label", type="password", key="admin_pw", placeholder="관리자 비밀번호", label_visibility="collapsed")
            if st.button("로그인", key="btn_admin"):
                admin_code = get_admin_password()
                if pw == admin_code:
                    st.session_state["login_type"] = "admin"
                    st.session_state["login_user"] = "ADMIN"
                    st.rerun()
                else:
                    st.error("비밀번호 불일치")

        with tab_user:
            st.write("")
            name = st.text_input("mgr_name", key="user_name", placeholder="아이디", label_visibility="collapsed")
            st.write("") # spacer
            input_pw = st.text_input("mgr_pw", type="password", key="user_pw", placeholder="비밀번호", label_visibility="collapsed")
            if st.button("로그인", key="btn_user"):
                user_info = manager_contacts.get(name.strip())
                if not user_info:
                    st.error("사용자 정보 없음")
                else:
                    real_tel = user_info.get("phone", "")
                    real_pw = real_tel[-4:] if len(real_tel) >= 4 else None
                    if real_pw and input_pw == real_pw:
                        st.session_state["login_type"] = "user"
                        st.session_state["login_user"] = name.strip()
                        st.rerun()
                    else:
                        st.error("비밀번호 불일치")

        with tab_branch:
            st.write("")
            branch_pws = get_branch_admin_passwords()
            branch = st.selectbox("b_sel", list(branch_pws.keys()), key="branch_select", label_visibility="collapsed")
            name = st.text_input("b_name", key="branch_admin_name", placeholder="담당자명", label_visibility="collapsed")
            pw = st.text_input("b_pw", type="password", key="branch_admin_pw", placeholder="보안코드", label_visibility="collapsed")
            if st.button("로그인", key="btn_branch"):
                correct_pw = branch_pws.get(branch)
                if pw == correct_pw:
                    st.session_state["login_type"] = "branch_admin"
                    st.session_state["login_user"] = name.strip()
                    st.session_state["login_branch"] = branch
                    st.rerun()
                else:
                    st.error("인증 실패")

def check_login():
    """세션 상태를 확인하고 로그인이 안되어 있으면 폼을 표시 후 중단"""
    # 세션 초기화
    if "login_type" not in st.session_state:
        st.session_state["login_type"] = None
    if "login_user" not in st.session_state:
        st.session_state["login_user"] = None
    
    return st.session_state["login_type"]
