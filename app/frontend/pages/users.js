async function UsersPage(){
  const { create, api, toast, setToken } = window.__APP__;
  const wrap = create('div','page-grid');

  const listCard = create('section','card');
  listCard.innerHTML = `
    <h2 class="card-title">Người dùng</h2>
    <div id="list" class="note"></div>
  `;
  wrap.appendChild(listCard);

  const formCard = create('section','card');
  formCard.innerHTML = `
    <h2 class="card-title">Thêm/ Sửa</h2>
    <div class="note">(Legacy) Dành cho dữ liệu demo. Hệ thống mới dùng tài khoản + profiles.</div>
    <div class="grid-2 gap">
      <div>
        <label class="label">Tên</label>
        <input id="name" class="input" placeholder="VD: Nguyễn Văn A"/>
      </div>
      <div>
        <label class="label">Tuổi</label>
        <input id="age" type="number" class="input" min="0" max="120" value="30"/>
      </div>
    </div>
    <label class="label mt">Bệnh lý/ dị ứng/ thuốc</label>
    <textarea id="cond" class="textarea" rows="4"></textarea>
    <div class="actions">
      <button id="btnCreate" class="btn btn-primary"><span class="spinner hidden"></span><span>Lưu mới</span></button>
      <button id="btnUpdate" class="btn"><span class="spinner hidden"></span><span>Cập nhật</span></button>
      <button id="btnDelete" class="btn"><span class="spinner hidden"></span><span>Xoá</span></button>
    </div>
  `;
  wrap.appendChild(formCard);

  let selectedId = null;

  async function reload(){
    const users = await api('/users');
    const box = listCard.querySelector('#list');
    if(users.length===0){ box.textContent='Chưa có người dùng.'; return; }
    box.innerHTML = users.map(u=>`<a href="#" data-id="${u.id}">${u.name} (id:${u.id}, tuổi:${u.age ?? ''})</a>`).join('<br/>');
    box.querySelectorAll('a').forEach(a=>{
      a.addEventListener('click', async (e)=>{
        e.preventDefault();
        selectedId = parseInt(a.dataset.id,10);
        toast(`Đã chọn id=${selectedId}`);
      });
    });
  }

  async function withBtn(btn, fn){
    const sp = btn.querySelector('.spinner'); sp.classList.remove('hidden'); btn.disabled = true; try{ await fn(); } finally { sp.classList.add('hidden'); btn.disabled=false; }
  }

  formCard.querySelector('#btnCreate').addEventListener('click', ()=> withBtn(formCard.querySelector('#btnCreate'), async ()=>{
    const body = { name: formCard.querySelector('#name').value.trim(), age: parseInt(formCard.querySelector('#age').value,10), conditions_text: formCard.querySelector('#cond').value };
    const res = await api('/users', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
    if(res.ok){ toast('Đã tạo'); await reload(); selectedId = res.user_id; }
    else toast('Tạo thất bại','error');
  }));

  formCard.querySelector('#btnUpdate').addEventListener('click', ()=> withBtn(formCard.querySelector('#btnUpdate'), async ()=>{
    if(!selectedId) return toast('Chọn user từ danh sách','error');
    const body = { name: formCard.querySelector('#name').value.trim(), age: parseInt(formCard.querySelector('#age').value,10), conditions_text: formCard.querySelector('#cond').value };
    const res = await api(`/users/${selectedId}`, { method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
    if(res.ok){ toast('Đã cập nhật'); await reload(); }
    else toast('Cập nhật thất bại','error');
  }));

  formCard.querySelector('#btnDelete').addEventListener('click', ()=> withBtn(formCard.querySelector('#btnDelete'), async ()=>{
    if(!selectedId) return toast('Chọn user từ danh sách','error');
    const res = await api(`/users/${selectedId}`, { method:'DELETE' });
    if(res.ok){ toast('Đã xoá'); selectedId=null; await reload(); }
    else toast('Xoá thất bại','error');
  }));

  await reload();
  return wrap;
}

window.__APP__.UsersPage = UsersPage;
window.addEventListener('load', ()=>{ window.__APP__.route && window.__APP__.route('/users', UsersPage); });


