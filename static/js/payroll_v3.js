/* Payroll V3 - prototype: chỉ mô phỏng UI trong bộ nhớ, không có AJAX hoặc ghi DB. */
(function () {
  'use strict';
  const root = document.querySelector('.hl-payroll');
  if (!root) return;
  const $ = id => document.getElementById(id);
  const money = n => Math.round(n).toLocaleString('vi-VN') + ' ₫';
  const escapeHtml = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  if (root.dataset.page === 'employee') {
    const setEmployeePeriod = () => {
      const available = $('hl-employee-period').value === '2026-10';
      $('hl-slip').classList.toggle('hl-hidden', !available);
      $('hl-no-slip').classList.toggle('hl-hidden', available);
      $('hl-print-slip').disabled = !available;
    };
    $('hl-employee-period').addEventListener('change', setEmployeePeriod);
    $('hl-print-slip').addEventListener('click', () => window.print());
    setEmployeePeriod();
    return;
  }

  const sample = [
    {id:'NV001',name:'Nguyễn Minh Anh',position:'Pha chế',regular:160,ot:12.5,rate:25000,allowance:300000,deduct:0},
    {id:'NV002',name:'Trần Hoàng Nam',position:'Phục vụ',regular:160,ot:8,rate:25000,allowance:250000,deduct:50000},
    {id:'NV003',name:'Lê Thị Thu Hà',position:'Thu ngân',regular:160,ot:4,rate:27000,allowance:200000,deduct:0},
    {id:'NV004',name:'Phạm Quốc Huy',position:'Pha chế',regular:152,ot:6,rate:25000,allowance:300000,deduct:50000},
    {id:'NV005',name:'Võ Ngọc Mai',position:'Phục vụ',regular:160,ot:0,rate:25000,allowance:200000,deduct:0},
    {id:'NV006',name:'Đặng Tuấn Kiệt',position:'Trưởng ca',regular:168,ot:10,rate:45000,allowance:550000,deduct:0}
  ];
  const salary = row => row.regular * row.rate + row.ot * 1.5 * row.rate + row.allowance - row.deduct;
  let employees = [];
  let isLocked = false;
  let selected = new Set();
  let tab = 'review';
  let modalReturnFocus = null;
  let activeModal = false;
  let toastTimeout;
  const hasPeriod = () => $('hl-period').value === '2026-10';

  function notify(message) {
    const el = $('hl-toast');
    el.textContent = message;
    el.classList.remove('hl-hidden');
    window.clearTimeout(toastTimeout);
    toastTimeout = window.setTimeout(() => el.classList.add('hl-hidden'), 4500);
  }
  function closeModal() {
    $('hl-modal').classList.add('hl-hidden');
    activeModal = false;
    $('hl-modal-confirm').onclick = null;
    if (modalReturnFocus && typeof modalReturnFocus.focus === 'function') modalReturnFocus.focus();
  }
  function showModal({title, message, details = '', confirmLabel = 'Xác nhận (demo)', onConfirm = null}) {
    modalReturnFocus = document.activeElement;
    activeModal = true;
    $('hl-modal-title').textContent = title;
    $('hl-modal-body').textContent = message;
    $('hl-modal-meta').textContent = details;
    $('hl-modal-meta').classList.toggle('hl-hidden', !details);
    $('hl-modal-confirm').textContent = confirmLabel;
    $('hl-modal-confirm').classList.toggle('hl-hidden', !onConfirm);
    $('hl-modal-cancel').textContent = onConfirm ? 'Hủy' : 'Đóng';
    $('hl-modal').classList.remove('hl-hidden');
    $('hl-modal-confirm').onclick = onConfirm ? () => {closeModal(); onConfirm();} : null;
    $('hl-modal-cancel').focus();
  }
  $('hl-modal-cancel').addEventListener('click', closeModal);
  $('hl-modal').addEventListener('click', ev => {if (ev.target === $('hl-modal')) closeModal();});
  document.addEventListener('keydown', ev => {
    if (!activeModal) return;
    if (ev.key === 'Escape') closeModal();
    if (ev.key === 'Tab') {
      const buttons = Array.from($('hl-modal').querySelectorAll('button:not(.hl-hidden):not(:disabled)'));
      const idx = buttons.indexOf(document.activeElement);
      if (ev.shiftKey && idx <= 0) { ev.preventDefault(); buttons[buttons.length-1].focus(); }
      else if (!ev.shiftKey && idx === buttons.length - 1) { ev.preventDefault(); buttons[0].focus(); }
    }
  });

  function clearFilters() {
    $('hl-review-search').value = '';
    $('hl-payment-search').value = '';
    $('hl-issued-filter').value = 'all';
    $('hl-paid-filter').value = 'all';
  }
  function reset() {
    employees = sample.map(row => ({...row, issued:false, paid:false}));
    selected.clear();
    isLocked = false;
    clearFilters();
    render();
  }
  function switchTab(next) {
    tab = next;
    root.querySelectorAll('[data-tab]').forEach(button => {
      const chosen = button.dataset.tab === tab;
      button.classList.toggle('active', chosen);
      chosen ? button.setAttribute('aria-current', 'step') : button.removeAttribute('aria-current');
    });
    ['review','finalize','payment'].forEach(name => $('hl-panel-' + name).classList.toggle('hl-hidden', tab !== name || !hasPeriod()));
    render();
  }
  function filtered(type) {
    const search = $('hl-' + type + '-search').value.trim().toLocaleLowerCase('vi');
    let data = employees.filter(row => (row.id + ' ' + row.name).toLocaleLowerCase('vi').includes(search));
    if (type === 'payment') {
      const issueFilter = $('hl-issued-filter').value;
      const paidFilter = $('hl-paid-filter').value;
      data = data.filter(row =>
        (issueFilter === 'all' || (issueFilter === 'issued' ? row.issued : !row.issued)) &&
        (paidFilter === 'all' || (paidFilter === 'paid' ? row.paid : !row.paid))
      );
    }
    return data;
  }
  function renderKpis() {
    const data = hasPeriod() ? employees : [];
    const values = [
      ['Nhân viên trong kỳ', String(data.length)],
      ['Trạng thái bảng công', hasPeriod() ? isLocked ? 'Đã chốt (demo)' : 'Chưa chốt' : 'Chưa có dữ liệu'],
      ['Tổng lương dự kiến', hasPeriod() ? money(data.reduce((n,row)=>n+salary(row),0)) : 'Chưa tính'],
      ['Phiếu đã phát hành', data.filter(row=>row.issued).length + '/' + data.length]
    ];
    $('hl-kpis').innerHTML = values.map(([label,value]) => `<article><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong></article>`).join('');
  }
  function renderReview() {
    const rows = filtered('review');
    $('hl-review-rows').innerHTML = rows.map(row => `<tr><td>${escapeHtml(row.id)}</td><td><strong>${escapeHtml(row.name)}</strong><small>${escapeHtml(row.position)}</small></td><td>${row.regular.toLocaleString('vi-VN')} giờ</td><td>${row.ot.toLocaleString('vi-VN')} giờ</td></tr>`).join('') || '<tr><td colspan="4" class="hl-muted">Không có nhân viên phù hợp.</td></tr>';
    $('hl-review-count').textContent = `Hiển thị ${rows.length}/${employees.length} nhân viên`;
    $('hl-review-state').textContent = isLocked ? 'Đã chốt (demo)' : 'Chưa chốt';
    $('hl-go-finalize').disabled = !hasPeriod();
  }
  function renderFinalize() {
    $('hl-final-rows').innerHTML = employees.map(row => `<tr><td>${escapeHtml(row.id)}</td><td><strong>${escapeHtml(row.name)}</strong><small>${escapeHtml(row.position)}</small></td><td>${money(row.rate)}</td><td>${row.regular}</td><td>${row.ot.toLocaleString('vi-VN')}</td><td>${money(row.regular * row.rate)}</td><td>${money(row.ot * 1.5 * row.rate)}</td><td>${money(row.allowance)}</td><td>${money(row.deduct)}</td><td><strong>${money(salary(row))}</strong></td></tr>`).join('');
    $('hl-final-total').innerHTML = `<tr><td colspan="9">Tổng quỹ lương dự kiến (demo)</td><td>${money(employees.reduce((sum,row) => sum+salary(row),0))}</td></tr>`;
    $('hl-final-state').textContent = isLocked ? 'Đã chốt (demo)' : 'Chưa chốt';
    $('hl-final-hint').textContent = isLocked ? 'Bảng công đã được chốt trong phiên demo. Phiếu lương mẫu đã được tạo và sẵn sàng để mô phỏng phát hành.' : 'Kiểm tra giờ công và đơn giá trước khi chốt. Đây chỉ là dữ liệu demo, không tạo dữ liệu thật.';
    $('hl-lock-demo').disabled = isLocked || !hasPeriod();
  }
  function renderPayments() {
    const rows = filtered('payment');
    $('hl-payment-rows').innerHTML = rows.map(row => `<tr><td><input type="checkbox" data-select="${row.id}" ${selected.has(row.id)?'checked':''} ${!isLocked?'disabled':''} aria-label="Chọn ${escapeHtml(row.name)}"></td><td>${escapeHtml(row.id)}</td><td><strong>${escapeHtml(row.name)}</strong><small>${escapeHtml(row.position)}</small></td><td><strong>${money(salary(row))}</strong></td><td><span class="hl-tag ${row.issued?'ok':''}">${row.issued?'Đã phát hành':'Chưa phát hành'}</span></td><td><span class="hl-tag ${row.paid?'ok':''}">${row.paid?'Đã trả':'Chưa trả'}</span></td><td><button type="button" class="hl-action" data-slip="${row.id}" ${!isLocked?'disabled':''}>Xem phiếu</button></td></tr>`).join('') || '<tr><td colspan="7" class="hl-muted">Không có kết quả phù hợp.</td></tr>';
    $('hl-payment-summary').textContent = `${employees.filter(row => row.issued).length}/${employees.length} phiếu đã phát hành · ${employees.filter(row=>row.paid).length}/${employees.length} đã trả · ${selected.size} được chọn`;
    $('hl-payment-state').textContent = isLocked ? 'Đã lập phiếu mẫu' : 'Chờ chốt công';
    $('hl-select-all').disabled = !isLocked || rows.length === 0;
    $('hl-select-all').checked = rows.length>0 && rows.every(row=>selected.has(row.id));
    $('hl-bulk-issue').disabled = !isLocked || !employees.some(row=>selected.has(row.id)&&!row.issued);
    $('hl-bulk-pay').disabled = !isLocked || !employees.some(row=>selected.has(row.id)&&row.issued&&!row.paid);
  }
  function render() {
    $('hl-period-empty').classList.toggle('hl-hidden', hasPeriod());
    ['review','finalize','payment'].forEach(name => $('hl-panel-' + name).classList.toggle('hl-hidden', !hasPeriod() || tab !== name));
    renderKpis();renderReview();renderFinalize();renderPayments();
  }
  $('hl-go-finalize').onclick = () => switchTab('finalize');
  $('hl-back-review').onclick = () => switchTab('review');
  $('hl-review-search').addEventListener('input',renderReview);
  ['hl-payment-search','hl-issued-filter','hl-paid-filter'].forEach(id => $(id).addEventListener(id.includes('search')?'input':'change',renderPayments));
  $('hl-lock-demo').onclick = () => {
    if (!hasPeriod() || isLocked) return;
    showModal({title:'Xác nhận chốt bảng công?',message:'Sau khi chốt, bảng công của kỳ này sẽ được khóa và dùng làm căn cứ lập bảng lương. Bạn chỉ nên tiếp tục khi đã kiểm tra đầy đủ giờ công và giờ OT.',details:'Kỳ công: Tháng 10/2026\nNgười chốt: Tài khoản Quản lý đang đăng nhập\nLưu ý: Mô phỏng, không lưu dữ liệu thật.',confirmLabel:'Chốt bảng công & tiếp tục (demo)',onConfirm:()=>{isLocked=true;selected.clear();notify('Đã mô phỏng chốt công và lập phiếu mẫu. Không thay đổi database.');switchTab('payment');}});
  };
  $('hl-payment-rows').addEventListener('change', event => {
    const id = event.target.dataset.select;
    if (!id || !isLocked) return;
    event.target.checked ? selected.add(id) : selected.delete(id);
    renderPayments();
  });
  $('hl-select-all').addEventListener('change', event => {
    if (!isLocked) return;
    filtered('payment').forEach(row => event.target.checked ? selected.add(row.id) : selected.delete(row.id));
    renderPayments();
  });
  $('hl-payment-rows').addEventListener('click', event => {
    const btn = event.target.closest('[data-slip]');
    if (!btn || !isLocked) return;
    const row = employees.find(r=>r.id===btn.dataset.slip);
    if (!row) return;
    showModal({title:'Chi tiết phiếu lương mẫu',message:`${row.name} (${row.id}) · Kỳ tháng 10/2026.`,details:`Lương chính: ${money(row.regular*row.rate)}\nLương OT (hệ số giả định): ${money(row.ot*1.5*row.rate)}\nPhụ cấp: ${money(row.allowance)}\nKhấu trừ: ${money(row.deduct)}\nLương thực nhận: ${money(salary(row))}\nPhát hành: ${row.issued?'Đã phát hành':'Chưa phát hành'} · Thanh toán: ${row.paid?'Đã trả':'Chưa trả'}\n(Tất cả đều là dữ liệu demo.)`});
  });
  $('hl-bulk-issue').onclick = () => {
    if (!isLocked) return;
    const pending = employees.filter(row => selected.has(row.id) && !row.issued);
    if (!pending.length) return notify('Hãy chọn ít nhất một phiếu chưa phát hành.');
    showModal({title:'Xác nhận phát hành phiếu lương?',message:`${pending.length} phiếu lương đã chọn sẽ được đánh dấu phát hành trong bản demo. Nhân viên chưa nhận thông báo thật.`,details:'Hệ thống chưa gửi email hoặc mở quyền xem phiếu thật. Chỉ mô phỏng trạng thái trên giao diện.',confirmLabel:'Phát hành phiếu (demo)',onConfirm:()=>{pending.forEach(row=>row.issued=true);selected.clear();render();notify('Đã mô phỏng phát hành phiếu. Không có thông báo nào được gửi.');}});
  };
  $('hl-bulk-pay').onclick = () => {
    if (!isLocked) return;
    const pending = employees.filter(row => selected.has(row.id) && row.issued && !row.paid);
    if (!pending.length) return notify('Chọn phiếu đã phát hành và chưa được chi trả.');
    const total = pending.reduce((sum,row)=>sum+salary(row),0);
    showModal({title:'Xác nhận đã chi trả lương?',message:'Chỉ xác nhận sau khi cửa hàng đã thực hiện thanh toán thực tế cho nhân viên. Hệ thống không chuyển tiền qua ngân hàng.',details:`Kỳ lương: Tháng 10/2026\nSố nhân viên: ${pending.length}\nTổng tiền: ${money(total)}\nChế độ demo: chỉ đổi trạng thái trên trình duyệt.`,confirmLabel:'Xác nhận đã trả (demo)',onConfirm:()=>{pending.forEach(row=>row.paid=true);selected.clear();render();notify('Đã mô phỏng xác nhận chi trả; không có giao dịch hay ghi nhận DB.');}});
  };
  $('hl-period').onchange = () => {reset();switchTab('review');if(!hasPeriod())notify('Kỳ này chưa có dữ liệu bảng công mẫu.');};
  $('hl-reset-demo').onclick = () => showModal({title:'Đặt lại dữ liệu minh họa?',message:'Mọi trạng thái chốt công, phát hành và chi trả giả lập trong phiên này sẽ được đưa về ban đầu.',confirmLabel:'Đặt lại demo',onConfirm:()=>{reset();switchTab('review');notify('Đã đặt lại dữ liệu demo.');}});
  root.querySelectorAll('[data-tab]').forEach(button => button.addEventListener('click',()=>switchTab(button.dataset.tab)));
  reset();switchTab('review');
})();
