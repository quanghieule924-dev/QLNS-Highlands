/* Payroll V4: Demo only. localStorage contains PUBLIC SAMPLE data, never put real payroll data here. */
(()=>{
'use strict';
const root=document.querySelector('.hl-payroll');if(!root)return;
const $=id=>document.getElementById(id);
const KEY='qlns_highlands_payroll_v4_DEMO';
const SAMPLE=[
{id:'NV001',name:'Nguyễn Minh Anh',position:'Pha chế',regular:160,ot:12.5,rate:25000,allowance:300000,deduct:0},
{id:'NV002',name:'Trần Hoàng Nam',position:'Phục vụ',regular:160,ot:8,rate:25000,allowance:250000,deduct:50000},
{id:'NV003',name:'Lê Thị Thu Hà',position:'Thu ngân',regular:160,ot:4,rate:27000,allowance:200000,deduct:0},
{id:'NV004',name:'Phạm Quốc Huy',position:'Pha chế',regular:152,ot:6,rate:25000,allowance:300000,deduct:50000},
{id:'NV005',name:'Võ Ngọc Mai',position:'Phục vụ',regular:160,ot:0,rate:25000,allowance:200000,deduct:0},
{id:'NV006',name:'Đặng Tuấn Kiệt',position:'Trưởng ca',regular:168,ot:10,rate:45000,allowance:550000,deduct:0}
];
const money=n=>Math.round(n).toLocaleString('vi-VN')+' ₫';
const fmtDate=d=>{if(!d)return '—';const v=d.split('-');return v.length===3?v.reverse().join('/'):d};
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const salary=r=>r.regular*r.rate+r.ot*1.5*r.rate+r.allowance-r.deduct;
const init=()=>({locked:false,employees:SAMPLE.map(e=>({...e,issued:false,paid:false,feedback:'none',paidDate:'',method:'',reference:''}))});
const validRow=r=>r&&typeof r.id==='string'&&typeof r.issued==='boolean'&&typeof r.paid==='boolean';
function load(){try{const value=JSON.parse(localStorage.getItem(KEY));if(value&&typeof value.locked==='boolean'&&Array.isArray(value.employees)&&value.employees.length===SAMPLE.length&&value.employees.every(validRow))return value}catch(e){}return init()}
function save(value){try{localStorage.setItem(KEY,JSON.stringify(value))}catch(e){}}
let state=load();
function toast(message){const e=$('hl-toast');if(!e)return;e.textContent=message;e.classList.remove('hl-hidden');clearTimeout(toast.timer);toast.timer=setTimeout(()=>e.classList.add('hl-hidden'),3500)}

if(root.dataset.page==='employee'){
 const employeeId='NV001'; // Demo cố định! Khi làm backend phải lấy từ liên kết request.user -> NhanVien.
 const period=$('hl-employee-period');const modal=$('hl-employee-modal');let pending=null;
 const row=()=>state.employees.find(r=>r.id===employeeId);
 function renderEmployee(){state=load();const r=row();const month=period.value==='2026-10';const issued=month&&r&&r.issued;
  $('hl-slip').classList.toggle('hl-hidden',!issued);$('hl-no-slip').classList.toggle('hl-hidden',!!issued);
  $('hl-receipt-panel').classList.toggle('hl-hidden',!issued);$('hl-print-slip').disabled=!issued;
  if(!issued){$('hl-no-slip').querySelector('p').textContent=month?'Phiếu lương kỳ này chưa được quản lý phát hành trong bản demo.':'Kỳ được chọn chưa có phiếu lương mẫu.';return}
  $('hl-slip-issued').textContent='Đã phát hành (demo)';$('hl-slip-issued').className='hl-state hl-success';
  const pay=r.paid?'Đã ghi nhận chi trả ('+fmtDate(r.paidDate)+')':'Chưa ghi nhận chi trả';
  $('hl-slip-paid').textContent=pay;$('hl-slip-paid-detail').textContent=pay;
  const status=r.feedback==='received'?'Đã xác nhận nhận lương':r.feedback==='issue'?'Báo chưa nhận lương':r.paid?'Chờ phản hồi':'Chờ chi trả';
  $('hl-receipt-status').textContent=status;$('hl-receipt-status').className='hl-state '+(r.feedback==='received'?'hl-success':'');
  const msg=r.feedback==='received'?'Bạn đã xác nhận nhận đủ lương trong bản demo.':r.feedback==='issue'?'Bạn đã báo chưa nhận lương; quản lý cần kiểm tra lại giao dịch.':r.paid?'Quản lý đã ghi nhận chi trả. Vui lòng kiểm tra tiền thực nhận trước khi phản hồi.':'Quản lý chưa ghi nhận chi trả. Bạn chưa thể phản hồi nhận lương.';
  $('hl-receipt-message').textContent=msg;
  $('hl-confirm-received').disabled=!r.paid||r.feedback!=='none';$('hl-report-issue').disabled=!r.paid||r.feedback!=='none';
 }
 function close(){modal.classList.add('hl-hidden');pending=null}
 function ask(kind){const r=row();if(!r||!r.issued||!r.paid||r.feedback!=='none')return;
  pending=kind;$('hl-employee-modal-title').textContent=kind==='received'?'Xác nhận đã nhận đủ lương?':'Thông báo chưa nhận lương?';
  $('hl-employee-modal-message').textContent=kind==='received'?'Bạn xác nhận đã thực sự nhận đủ '+money(salary(r))+' cho kỳ tháng 10/2026. Đây chỉ là dữ liệu demo.':'Bạn xác nhận chưa nhận được khoản lương này. Trạng thái sẽ chuyển sang “Báo chưa nhận” để quản lý theo dõi trong bản demo.';
  modal.classList.remove('hl-hidden');$('hl-employee-cancel').focus();
 }
 $('hl-confirm-received').onclick=()=>ask('received');$('hl-report-issue').onclick=()=>ask('issue');
 $('hl-employee-cancel').onclick=close;
 modal.addEventListener('click',e=>{if(e.target===modal)close()});
 $('hl-employee-confirm').onclick=()=>{if(!pending)return;state=load();const r=row();if(!r||!r.issued||!r.paid||r.feedback!=='none'){close();return}r.feedback=pending;save(state);close();renderEmployee();toast('Đã lưu phản hồi minh họa trên trình duyệt.')};
 period.onchange=renderEmployee;$('hl-print-slip').onclick=()=>window.print();
 window.addEventListener('storage',e=>{if(e.key===KEY)renderEmployee()});document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});
 renderEmployee();return;
}
let selected=new Set(),tab='review',modalReturn=null,modalHandler=null;
const hasPeriod=()=>$('hl-period').value==='2026-10';
function closeModal(){$('hl-modal').classList.add('hl-hidden');$('hl-payment-fields').classList.add('hl-hidden');modalHandler=null;if(modalReturn?.focus)modalReturn.focus()}
function showModal({title,message,details='',button='Xác nhận (demo)',payment=false,action=null}){
 modalReturn=document.activeElement;modalHandler=action;$('hl-modal-title').textContent=title;$('hl-modal-body').textContent=message;
 $('hl-modal-meta').textContent=details;$('hl-modal-meta').classList.toggle('hl-hidden',!details);
 $('hl-payment-fields').classList.toggle('hl-hidden',!payment);
 if(payment){$('hl-method').value='Chuyển khoản';$('hl-pay-date').value=new Date().toLocaleDateString('en-CA');$('hl-pay-ref').value=''}
 $('hl-modal-confirm').textContent=button;$('hl-modal-confirm').classList.toggle('hl-hidden',!action);$('hl-modal-cancel').textContent=action?'Hủy':'Đóng';
 $('hl-modal').classList.remove('hl-hidden');$('hl-modal-cancel').focus();
}
$('hl-modal-cancel').onclick=closeModal;
$('hl-modal').addEventListener('click',e=>{if(e.target===$('hl-modal'))closeModal()});
$('hl-modal-confirm').onclick=()=>{if(!modalHandler)return;const payload={method:$('hl-method').value,paidDate:$('hl-pay-date').value,reference:$('hl-pay-ref').value.trim()};if(!$('hl-payment-fields').classList.contains('hl-hidden')&&!payload.paidDate){toast('Vui lòng chọn ngày ghi nhận chi trả.');return}const cb=modalHandler;closeModal();cb(payload)};
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('hl-modal').classList.contains('hl-hidden'))closeModal()});
function resetFilters(){['hl-review-search','hl-payment-search'].forEach(id=>$(id).value='');['hl-issued-filter','hl-paid-filter','hl-feedback-filter'].forEach(id=>$(id).value='all')}
function reset(){state=init();save(state);selected.clear();resetFilters();render()}
function switchTab(next){tab=next;root.querySelectorAll('[data-tab]').forEach(b=>{b.classList.toggle('active',b.dataset.tab===next);b.dataset.tab===next?b.setAttribute('aria-current','step'):b.removeAttribute('aria-current')});render()}
function filtered(type){const q=$('hl-'+type+'-search').value.trim().toLocaleLowerCase('vi');let rows=state.employees.filter(r=>(r.id+' '+r.name).toLocaleLowerCase('vi').includes(q));if(type==='payment'){
 rows=rows.filter(r=>
   ($('hl-issued-filter').value==='all' || (($('hl-issued-filter').value==='issued')===r.issued)) &&
   ($('hl-paid-filter').value==='all' || (($('hl-paid-filter').value==='paid')===r.paid)) &&
   ($('hl-feedback-filter').value==='all' || $('hl-feedback-filter').value===r.feedback)
 );
 }return rows}
function badge(text,cls){return '<span class="hl-tag '+cls+'">'+esc(text)+'</span>'}
function renderKpis(){const rows=hasPeriod()?state.employees:[];const items=[['Nhân viên trong kỳ',rows.length],['Trạng thái bảng công',hasPeriod()?(state.locked?'Đã chốt (demo)':'Chưa chốt'):'Chưa có dữ liệu'],['Tổng lương dự kiến',hasPeriod()?money(rows.reduce((s,r)=>s+salary(r),0)):'Chưa tính'],['Đã phát hành / phản hồi',rows.filter(r=>r.issued).length+'/'+rows.length+' · '+rows.filter(r=>r.feedback!=='none').length+' phản hồi']];$('hl-kpis').innerHTML=items.map(([label,v])=>'<article><small>'+esc(label)+'</small><strong>'+esc(v)+'</strong></article>').join('')}
function renderReview(){const rows=filtered('review');$('hl-review-rows').innerHTML=rows.map(r=>'<tr><td>'+esc(r.id)+'</td><td><strong>'+esc(r.name)+'</strong><small>'+esc(r.position)+'</small></td><td>'+r.regular.toLocaleString('vi-VN')+' giờ</td><td>'+r.ot.toLocaleString('vi-VN')+' giờ</td></tr>').join('')||'<tr><td colspan="4" class="hl-muted">Không có nhân viên phù hợp.</td></tr>';$('hl-review-count').textContent=`${rows.length}/${state.employees.length} nhân viên`;$('hl-review-state').textContent=state.locked?'Đã chốt (demo)':'Chưa chốt';$('hl-go-finalize').disabled=!hasPeriod()}
function renderFinalize(){$('hl-final-rows').innerHTML=state.employees.map(r=>'<tr><td>'+esc(r.id)+'</td><td><strong>'+esc(r.name)+'</strong><small>'+esc(r.position)+'</small></td><td>'+money(r.rate)+'</td><td>'+r.regular+'</td><td>'+r.ot.toLocaleString('vi-VN')+'</td><td>'+money(r.regular*r.rate)+'</td><td>'+money(r.ot*1.5*r.rate)+'</td><td>'+money(r.allowance)+'</td><td>'+money(r.deduct)+'</td><td><strong>'+money(salary(r))+'</strong></td></tr>').join('');$('hl-final-total').innerHTML='<tr><td colspan="9">Tổng lương dự kiến (demo)</td><td>'+money(state.employees.reduce((s,r)=>s+salary(r),0))+'</td></tr>';$('hl-final-state').textContent=state.locked?'Đã chốt (demo)':'Chưa chốt';$('hl-final-hint').textContent=state.locked?'Đã chốt công trong bản demo. Có thể chuyển đến bước phát hành phiếu.':'Kiểm tra giờ công và đơn giá trước khi chốt; chưa có thay đổi nào trên SQLite.';$('hl-lock-demo').disabled=state.locked||!hasPeriod()}
function renderPayment(){const rows=filtered('payment');$('hl-payment-rows').innerHTML=rows.map(r=>'<tr><td><input type="checkbox" data-select="'+esc(r.id)+'" '+(selected.has(r.id)?'checked ':'')+(!state.locked?'disabled ':'')+'aria-label="Chọn '+esc(r.name)+'"></td><td>'+esc(r.id)+'</td><td><strong>'+esc(r.name)+'</strong><small>'+esc(r.position)+'</small></td><td><strong>'+money(salary(r))+'</strong></td><td>'+badge(r.issued?'Đã phát hành':'Chưa phát hành',r.issued?'blue':'amber')+'</td><td>'+badge(r.paid?'Đã ghi nhận':'Chưa ghi nhận',r.paid?'ok':'amber')+(r.paid?'<small>'+fmtDate(r.paidDate)+'</small>':'')+'</td><td>'+badge(r.feedback==='received'?'Đã nhận lương':r.feedback==='issue'?'Báo chưa nhận':'Chưa phản hồi',r.feedback==='received'?'ok':r.feedback==='issue'?'danger':'neutral')+'</td><td><button type="button" class="hl-action" data-slip="'+esc(r.id)+'" '+(!state.locked?'disabled':'')+'>Xem phiếu</button></td></tr>').join('')||'<tr><td colspan="8" class="hl-muted">Không có dữ liệu phù hợp.</td></tr>';
 $('hl-payment-summary').textContent=`${state.employees.filter(r=>r.issued).length}/${state.employees.length} phát hành · ${state.employees.filter(r=>r.paid).length} ghi nhận chi trả · ${state.employees.filter(r=>r.feedback==='received').length} đã nhận · ${state.employees.filter(r=>r.feedback==='issue').length} báo chưa nhận · ${selected.size} chọn`;
 $('hl-payment-state').textContent=state.locked?'Đã tạo phiếu mẫu':'Chờ chốt công';$('hl-select-all').disabled=!state.locked||!rows.length;$('hl-select-all').checked=!!rows.length&&rows.every(r=>selected.has(r.id));$('hl-bulk-issue').disabled=!state.locked||!state.employees.some(r=>selected.has(r.id)&&!r.issued);$('hl-bulk-pay').disabled=!state.locked||!state.employees.some(r=>selected.has(r.id)&&r.issued&&!r.paid);
}
function render(){$('hl-period-empty').classList.toggle('hl-hidden',hasPeriod());['review','finalize','payment'].forEach(n=>$('hl-panel-'+n).classList.toggle('hl-hidden',!hasPeriod()||tab!==n));renderKpis();renderReview();renderFinalize();renderPayment()}
$('hl-go-finalize').onclick=()=>switchTab('finalize');$('hl-back-review').onclick=()=>switchTab('review');$('hl-review-search').oninput=renderReview;['hl-payment-search','hl-issued-filter','hl-paid-filter','hl-feedback-filter'].forEach(id=>$(id).addEventListener(id.includes('search')?'input':'change',renderPayment));
$('hl-lock-demo').onclick=()=>{if(!hasPeriod()||state.locked)return;showModal({title:'Xác nhận chốt bảng công?',message:'Sau khi chốt, bảng công của kỳ này sẽ được khóa và dùng làm căn cứ lập bảng lương. Bạn chỉ nên tiếp tục khi đã kiểm tra đầy đủ giờ công và OT.',details:'Kỳ: Tháng 10/2026\nĐây chỉ là trạng thái DEMO.',button:'Chốt công & tiếp tục (demo)',action:()=>{state.locked=true;save(state);selected.clear();switchTab('payment');toast('Đã mô phỏng chốt công, không ghi SQLite.')}})};
$('hl-payment-rows').addEventListener('change',e=>{const id=e.target.dataset.select;if(!id||!state.locked)return;e.target.checked?selected.add(id):selected.delete(id);renderPayment()});
$('hl-select-all').onchange=e=>{filtered('payment').forEach(r=>e.target.checked?selected.add(r.id):selected.delete(r.id));renderPayment()};
$('hl-payment-rows').addEventListener('click',e=>{const b=e.target.closest('[data-slip]');if(!b)return;const r=state.employees.find(x=>x.id===b.dataset.slip);if(!r)return;showModal({title:'Phiếu lương mẫu: '+r.id,message:r.name+' · Kỳ 10/2026',details:`Lương chính: ${money(r.regular*r.rate)}\nLương OT: ${money(r.ot*1.5*r.rate)}\nPhụ cấp: ${money(r.allowance)}\nKhấu trừ: ${money(r.deduct)}\nThực nhận: ${money(salary(r))}\nPhát hành: ${r.issued?'Đã':'Chưa'}\nChi trả: ${r.paid?'Đã ghi nhận':'Chưa ghi nhận'}\nPhản hồi: ${r.feedback==='received'?'Đã nhận':r.feedback==='issue'?'Báo chưa nhận':'Chưa phản hồi'}`})});
$('hl-bulk-issue').onclick=()=>{if(!state.locked)return;const ids=state.employees.filter(r=>selected.has(r.id)&&!r.issued).map(r=>r.id);if(!ids.length)return;showModal({title:'Phát hành phiếu lương?',message:`Đánh dấu phát hành ${ids.length} phiếu mẫu. Phiếu NV001 sẽ có thể xem trên giao diện Nhân viên bản demo.`,button:'Phát hành (demo)',action:()=>{state.employees.filter(r=>ids.includes(r.id)).forEach(r=>r.issued=true);save(state);selected.clear();render();toast('Đã mô phỏng phát hành phiếu.')}})};
$('hl-bulk-pay').onclick=()=>{if(!state.locked)return;const ids=state.employees.filter(r=>selected.has(r.id)&&r.issued&&!r.paid).map(r=>r.id);if(!ids.length)return;const amount=state.employees.filter(r=>ids.includes(r.id)).reduce((s,r)=>s+salary(r),0);showModal({title:'Ghi nhận đã chi trả lương?',message:'Chỉ ghi nhận khi cửa hàng đã chuyển khoản hoặc thanh toán thực tế ngoài website. Sau đó nhân viên có thể phản hồi đã nhận hoặc chưa nhận.',details:`${ids.length} nhân viên · Tổng tiền ${money(amount)}\nKhông có giao dịch ngân hàng được thực hiện.`,button:'Ghi nhận chi trả (demo)',payment:true,action:({method,paidDate,reference})=>{state.employees.filter(r=>ids.includes(r.id)).forEach(r=>{r.paid=true;r.method=method;r.paidDate=paidDate;r.reference=reference;r.feedback='none'});save(state);selected.clear();render();toast('Đã ghi nhận trạng thái DEMO. Nhân viên NV001 có thể phản hồi trên trang phiếu mẫu.')}})};
$('hl-period').onchange=()=>{selected.clear();switchTab('review');if(!hasPeriod())toast('Chưa có dữ liệu demo cho kỳ này.')};$('hl-reset-demo').onclick=()=>showModal({title:'Đặt lại toàn bộ dữ liệu demo?',message:'Thao tác đưa tất cả trạng thái phát hành, chi trả và phản hồi của cả hai trang về ban đầu trong trình duyệt này.',button:'Đặt lại demo',action:()=>{reset();switchTab('review');toast('Đã đặt lại dữ liệu demo.')}});
root.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>switchTab(b.dataset.tab));window.addEventListener('storage',e=>{if(e.key===KEY){state=load();render()}});
switchTab('review');
})();
