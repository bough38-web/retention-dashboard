
// Python에서 주입된 CSV 데이터
const MASTER_CSV = `지사명,구역코드,담당자명,신규목표,해지목표,휴대폰뒷자리
중앙지사,G000103,김의겸,50,2,0000
중앙지사,G000203,최용호,40,3,1234
중앙지사,G000401,송민철,50,1,0000
중앙지사,G000402,김병조,30,0,0000
중앙지사,G000409,미지정,20,0,0000
강북지사,G000101,성진수,60,5,0000
강북지사,G000102,정민석,50,2,5678
서대문지사,G000201,유범식,45,2,0000`;

const app = {
    user: null, 
    // Centralized Config & Credentials
    config: JSON.parse(localStorage.getItem('sa_pro_config')) || { 
        fee: 30, 
        theme: 'light',
        auth: {
            admin: { id: 'admin', pw: '1234' },
            branch: { pw: '1234' },
            defaultPw: '0000'
        }
    },
    data: JSON.parse(localStorage.getItem('sa_pro_data')) || [],
    sortDir: 1,

    init: function() {
        this.applyTheme(this.config.theme);
        if(!this.data || this.data.length === 0) this.initData(false);
        this.updateLoginOptions();
        
        // 세션 자동 복구
        const savedUser = sessionStorage.getItem('sa_user');
        if(savedUser) { 
            try {
                this.user = JSON.parse(savedUser); 
                this.onLoginSuccess(); 
            } catch(e) {
                sessionStorage.removeItem('sa_user');
            }
        }
    },

    showToast: function(msg, type='info') {
        const el = document.createElement('div');
        el.className = 'toast';
        el.style.borderLeftColor = type === 'success' ? '#2ecc71' : (type === 'error' ? '#e74c3c' : '#4e54c8');
        el.innerHTML = `<span>${type==='success'?'✅':'ℹ️'}</span> <div>${msg}</div>`;
        const container = document.getElementById('toastContainer');
        if(container) container.appendChild(el);
        setTimeout(() => el.remove(), 3000);
    },

    toggleTheme: function() {
        this.config.theme = this.config.theme === 'light' ? 'dark' : 'light';
        localStorage.setItem('sa_pro_config', JSON.stringify(this.config));
        this.applyTheme(this.config.theme);
    },
    applyTheme: function(theme) {
        document.documentElement.setAttribute('data-theme', theme);
    },

    setLoginMode: function(mode) {
        ['Admin','Branch','Staff'].forEach(m => {
            const el = document.getElementById('form'+m);
            if(el) el.style.display = 'none';
        });
        const target = document.getElementById('form'+(mode.charAt(0)+mode.slice(1).toLowerCase()));
        if(target) target.style.display = 'block';
    },
    updateLoginOptions: function() {
        // Handle case where data might be empty or malformed
        const branches = this.data ? [...new Set(this.data.map(d => d.branch))].filter(Boolean) : [];
        const opts = '<option value="">Select Branch</option>' + branches.map(b => `<option value="${b}">${b}</option>`).join('');
        const brSelect = document.getElementById('loginBranchSelect');
        const stSelect = document.getElementById('loginStaffBranch');
        if(brSelect) brSelect.innerHTML = opts;
        if(stSelect) stSelect.innerHTML = opts;
    },
    updateLoginStaffList: function() { // Added missing logical implementation
        const br = document.getElementById('loginStaffBranch').value;
        const staffList = this.data.filter(d => d.branch === br).map(d => d.manager);
        // Optionally update a datalist or similar if we were using a select for names, 
        // but current UI uses text input for name, so we just return.
    },

    login: function() {
        const roleInput = document.querySelector('input[name="role"]:checked');
        if(!roleInput) return;
        const role = roleInput.value;
        let u = null;
        
        // Use credentials from config
        if(role === 'ADMIN') {
            const id = document.getElementById('adminId').value;
            const pw = document.getElementById('adminPw').value;
            if(id === this.config.auth.admin.id && pw === this.config.auth.admin.pw)
                u = { role, name: 'Administrator', branch: 'HQ' };
        } else if(role === 'BRANCH') {
            const br = document.getElementById('loginBranchSelect').value;
            const pw = document.getElementById('branchPw').value;
            if(br && pw === this.config.auth.branch.pw) u = { role, name: br + ' Manager', branch: br };
        } else if(role === 'STAFF') {
            const br = document.getElementById('loginStaffBranch').value;
            const nm = document.getElementById('loginStaffName').value.trim();
            const pw = document.getElementById('staffPw').value.trim();
            
            if(br && nm) {
                const t = this.data.find(d => d.branch === br && d.manager === nm);
                if(t) {
                    const savedPw = t.phone || this.config.auth.defaultPw;
                    if(savedPw === pw) u = { role, name: nm, branch: br };
                }
            }
        }

        if(u) {
            this.user = u;
            sessionStorage.setItem('sa_user', JSON.stringify(u));
            this.onLoginSuccess();
            this.showToast(`Welcome back, ${u.name}!`, 'success');
        } else {
            this.showToast('Login failed. Please check your credentials.', 'error');
        }
    },
    onLoginSuccess: function() {
        const loginScreen = document.getElementById('loginScreen');
        const appContainer = document.querySelector('.app-container');
        
        if(loginScreen) loginScreen.style.display = 'none';
        if(appContainer) appContainer.style.display = 'flex';
        
        const userInfo = document.getElementById('displayUserInfo');
        if(userInfo) userInfo.innerHTML = `<b>${this.user.name}</b><br><small>${this.user.role}</small>`;
        
        document.querySelectorAll('.admin-only').forEach(e => e.style.display = this.user.role === 'ADMIN' ? 'block' : 'none');
        
        const dateEl = document.getElementById('todayDate');
        if(dateEl) dateEl.innerText = new Date().toLocaleDateString();
        this.renderAll();
    },
    logout: function() {
        sessionStorage.removeItem('sa_user');
        location.reload();
    },

    initData: function(alertMsg=true) {
        if(!MASTER_CSV) return;
        const lines = MASTER_CSV.split('\n');
        this.data = [];
        for(let i=1; i<lines.length; i++) {
            const line = lines[i].trim();
            if(!line) continue;
            
            const p = line.split(',');
            if(p.length < 3) continue; // Basic validation
            
            this.data.push({
                id: Date.now() + i, 
                branch: p[0].trim(), 
                code: p[1].trim(), 
                manager: p[2].trim(),
                targetNew: Number(p[3])||0, 
                targetCancel: Number(p[4])||0, 
                phone: p[5]?p[5].trim():'0000',
                nc:0, cc:0, sus:0, ret:0, note:''
            });
        }
        this.save();
        if(alertMsg) this.showToast('Data initialized successfully.', 'success');
        this.updateLoginOptions();
        this.renderAll();
    },

    sortList: function(key) {
        this.sortDir *= -1;
        this.data.sort((a,b) => {
            let vA = a[key], vB = b[key];
            if(key === 'rate') { 
                // Safe division
                vA = a.targetNew > 0 ? a.nc/a.targetNew : 0; 
                vB = b.targetNew > 0 ? b.nc/b.targetNew : 0; 
            }
            if (typeof vA === 'string') vA = vA.toLowerCase();
            if (typeof vB === 'string') vB = vB.toLowerCase();
            
            if (vA < vB) return -this.sortDir;
            if (vA > vB) return this.sortDir;
            return 0;
        });
        this.renderList();
    },
    filterList: function() {
        this.renderList();
    },

    renderAll: function() { this.renderDashboard(); this.renderList(); },
    
    renderList: function() {
        const tbody = document.getElementById('listBody');
        const searchInput = document.getElementById('searchInput');
        const search = searchInput ? searchInput.value.toLowerCase() : '';
        const filterBranch = document.getElementById('filterBranch');
        const brFilter = filterBranch ? filterBranch.value : 'ALL';
        const u = this.user;

        if(!tbody) return;

        let list = this.data.filter(d => {
            if(u.role === 'BRANCH' && d.branch !== u.branch) return false;
            if(u.role === 'STAFF' && (d.branch !== u.branch || d.manager !== u.name)) return false;
            if(brFilter !== 'ALL' && d.branch !== brFilter) return false;
            return d.manager.toLowerCase().includes(search) || d.branch.toLowerCase().includes(search);
        });

        if(list.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:20px;">No data found.</td></tr>';
            return;
        }

        tbody.innerHTML = list.map(d => {
            // Robust calculation
            const r = d.targetNew > 0 ? Math.round((d.nc/d.targetNew)*100) : 0;
            return `<tr>
                <td><b>${d.branch}</b></td>
                <td>${d.manager} <span style="font-size:11px; color:#888;">${d.code}</span></td>
                <td>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <div style="flex:1; height:6px; background:#eee; border-radius:3px; overflow:hidden;">
                            <div style="width:${Math.min(r,100)}%; background:var(--primary); height:100%;"></div>
                        </div>
                        <span style="font-size:12px; font-weight:bold;">${r}%</span>
                    </div>
                    <div style="font-size:11px; color:#888;">${d.nc} / ${d.targetNew}</div>
                </td>
                <td><span style="color:#f54a45; font-weight:bold;">${d.cc}</span> <small>/ ${d.targetCancel}</small></td>
                <td>💎 ${d.ret}</td>
                <td><button onclick="app.openModal(${d.id})" class="btn-gradient" style="padding:6px 12px; font-size:12px;">Edit</button></td>
            </tr>`;
        }).join('');
        
        // Update Filter Dropdown for Admin
        if(u.role === 'ADMIN' && filterBranch) {
            const currentOpts = new Set(Array.from(filterBranch.options).map(o => o.value));
            const brs = [...new Set(this.data.map(d=>d.branch))];
            
            brs.forEach(b => {
                if(!currentOpts.has(b)) {
                    const opt = document.createElement('option');
                    opt.value = b;
                    opt.innerText = b;
                    filterBranch.appendChild(opt);
                }
            });
        }
    },
    
    renderDashboard: function() {
        const sum = k => this.data.reduce((a,b) => {
            if(this.user.role === 'BRANCH' && b.branch !== this.user.branch) return a;
            if(this.user.role === 'STAFF' && b.manager !== this.user.name) return a;
            return a + (b[k]||0);
        }, 0);

        const nc = sum('nc'), tn = sum('targetNew'), cc = sum('cc'), tc = sum('targetCancel');
        
        // Safe calculations
        const rateNew = tn > 0 ? (nc/tn)*100 : 0;
        const rateCancel = tc > 0 ? (cc/tc)*100 : 0;

        const updateEl = (id, txt) => { const el = document.getElementById(id); if(el) el.innerText = txt; };
        const setProp = (id, prop, val) => { const el = document.getElementById(id); if(el) el.style.setProperty(prop, val); };

        setProp('progNew', '--p', rateNew);
        updateEl('rateNew', Math.round(rateNew) + '%');
        updateEl('txtNewAct', nc); 
        updateEl('txtNewTarget', tn);

        setProp('progCancel', '--p', rateCancel);
        updateEl('rateCancel', Math.round(rateCancel) + '%');
        updateEl('txtCancelAct', cc); 
        updateEl('txtCancelTarget', tc);

        const totalMoney = (nc-cc) * this.config.fee;
        const moneyStr = totalMoney.toLocaleString();
        updateEl('totalMoney', moneyStr);
        updateEl('headRevenue', moneyStr);
        
        let inc = 0;
        this.data.forEach(d => {
            if(d.targetNew > 0 && (d.nc/d.targetNew) >= 1) inc += d.nc * 10000;
        });
        updateEl('estIncentive', inc.toLocaleString() + '원');

        // Chart
        const bMap = {};
        this.data.forEach(d => {
            if(!bMap[d.branch]) bMap[d.branch] = {act:0, tgt:0};
            bMap[d.branch].act += d.nc; bMap[d.branch].tgt += d.targetNew;
        });
        
        const ctx = document.getElementById('myChart');
        if(ctx) {
            if(this.chart) this.chart.destroy();
            this.chart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: Object.keys(bMap),
                    datasets: [
                        { label: 'Actual', data: Object.values(bMap).map(v=>v.act), backgroundColor: '#4e54c8', borderRadius: 6 },
                        { label: 'Target', data: Object.values(bMap).map(v=>v.tgt), type:'line', borderColor: '#00d2d3', borderWidth: 2, pointRadius: 0 }
                    ]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
            });
        }
    },

    openModal: function(id) {
        const t = this.data.find(d => d.id === id);
        if(!t) return;
        
        const setVal = (id, val) => { const el = document.getElementById(id); if(el) el.value = val; };
        
        setVal('editId', id);
        const infoEl = document.getElementById('modalInfo');
        if(infoEl) infoEl.innerHTML = `<b>${t.branch}</b> / ${t.manager}`;
        
        setVal('inpNew', t.nc);
        setVal('inpCancel', t.cc);
        setVal('inpSuspend', t.sus);
        setVal('inpRetention', t.ret);
        setVal('inpNote', t.note);
        
        const inpNew = document.getElementById('inpNew');
        if(inpNew) {
            inpNew.oninput = (e) => {
                const val = Number(e.target.value);
                const inc = (t.targetNew > 0 && (val/t.targetNew) >= 1) ? val * 10000 : 0;
                const prevEl = document.getElementById('previewInc');
                if(prevEl) prevEl.innerText = inc.toLocaleString();
            };
            // Trigger input to show initial calculation
            inpNew.dispatchEvent(new Event('input'));
        }
        
        document.getElementById('inputModal').style.display = 'flex';
    },
    closeModal: function() { document.getElementById('inputModal').style.display = 'none'; },
    saveModalData: function() {
        const idVal = document.getElementById('editId').value;
        const id = Number(idVal);
        const t = this.data.find(d => d.id === id);
        if(t) {
            t.nc = Number(document.getElementById('inpNew').value) || 0;
            t.cc = Number(document.getElementById('inpCancel').value) || 0;
            t.sus = Number(document.getElementById('inpSuspend').value) || 0;
            t.ret = Number(document.getElementById('inpRetention').value) || 0;
            t.note = document.getElementById('inpNote').value;
            this.save();
            this.closeModal();
            this.renderAll();
            this.showToast('Data saved successfully!', 'success');
        }
    },

    backupData: function() {
        const blob = new Blob([JSON.stringify(this.data)], {type: 'application/json'});
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `sales_backup_${new Date().toISOString().slice(0,10)}.json`;
        link.click();
    },
    restoreData: function(input) {
        const file = input.files[0];
        if(!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                this.data = JSON.parse(e.target.result);
                this.save();
                this.renderAll();
                this.updateLoginOptions();
                this.showToast('Data restored successfully.', 'success');
            } catch(err) { this.showToast('Invalid file format.', 'error'); }
        };
        reader.readAsText(file);
    },

    // Utilities
    save: function() { localStorage.setItem('sa_pro_data', JSON.stringify(this.data)); },
    initializeData: function() { if(confirm('Reset all data?')) this.initData(); },
    showTab: function(id) { 
        document.querySelectorAll('.page').forEach(e=>e.classList.remove('active'));
        document.querySelectorAll('.nav-item').forEach(e=>e.classList.remove('active'));
        const target = document.getElementById(id);
        if(target) target.classList.add('active'); 
    },
    updateFee: function() { 
        this.config.fee = Number(document.getElementById('inpFee').value); 
        localStorage.setItem('sa_pro_config', JSON.stringify(this.config)); 
        this.renderDashboard(); 
        this.showToast('Fee updated.'); 
    },
    downloadCSV: function() {
        let csv = "Branch,Code,Manager,New,Target,Cancel,TargetCancel,Suspend,Retention,Note\n";
        this.data.forEach(d => csv += `${d.branch},${d.code},${d.manager},${d.nc},${d.targetNew},${d.cc},${d.targetCancel},${d.sus},${d.ret},${d.note}\n`);
        const link = document.createElement("a"); 
        link.href = URL.createObjectURL(new Blob(["\uFEFF"+csv], {type: 'text/csv;charset=utf-8;'})); 
        link.download="sales_report.csv"; 
        link.click();
    }
};

window.onload = function() { app.init(); };
