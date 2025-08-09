const apiBase = '';
let currentUserId = null;

function log(msg) {
  const el = document.getElementById('log');
  el.textContent += `${msg}\n`;
}

function toast(message, type = 'success') {
  const t = document.getElementById('toast');
  t.textContent = message;
  t.className = `toast ${type}`;
  t.classList.remove('hidden');
  setTimeout(() => t.classList.add('hidden'), 2400);
}

function setLoading(btn, loading) {
  const spinner = btn.querySelector('.spinner');
  if (!spinner) return;
  if (loading) spinner.classList.remove('hidden'); else spinner.classList.add('hidden');
  btn.disabled = !!loading;
}

async function loadUsers() {
  const res = await fetch(`${apiBase}/users`);
  const users = await res.json();
  const sel = document.getElementById('userSelect');
  sel.innerHTML = '';
  users.forEach(u => {
    const opt = document.createElement('option');
    opt.value = u.id;
    opt.textContent = `${u.name} (id:${u.id})`;
    sel.appendChild(opt);
  });
}

async function saveProfile() {
  const btn = document.getElementById('btnSaveProfile');
  setLoading(btn, true);
  try {
    const body = {
    name: document.getElementById('name').value.trim(),
    age: parseInt(document.getElementById('age').value, 10),
    conditions_text: document.getElementById('conditions').value,
    };
    const res = await fetch(`${apiBase}/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (data.ok) {
      currentUserId = data.user_id;
      log(`Saved profile, user_id=${currentUserId}`);
      toast('Đã lưu hồ sơ', 'success');
      await loadUsers();
    } else {
      toast('Lưu hồ sơ thất bại', 'error');
    }
  } catch (e) {
    toast('Lỗi kết nối khi lưu hồ sơ', 'error');
  } finally {
    setLoading(btn, false);
  }
}

async function uploadPdf() {
  const btn = document.getElementById('btnUploadPdf');
  setLoading(btn, true);
  if (!currentUserId) {
    const sel = document.getElementById('userSelect');
    currentUserId = parseInt(sel.value, 10) || null;
  }
  if (!currentUserId) return alert('Chọn hồ sơ trước');

  const file = document.getElementById('pdfFile').files[0];
  if (!file) return alert('Chọn file PDF');
  try {
    const fd = new FormData();
    fd.append('user_id', currentUserId);
    fd.append('file', file);
    const res = await fetch(`${apiBase}/upload_pdf`, { method: 'POST', body: fd });
    const data = await res.json();
    if (data.ok) {
      document.getElementById('pdfSummary').textContent = data.summary || '';
      log(`Uploaded PDF, document_id=${data.document_id}`);
      toast('Đã upload PDF', 'success');
    } else {
      toast('Upload PDF thất bại', 'error');
    }
  } catch (e) {
    toast('Lỗi kết nối khi upload', 'error');
  } finally {
    setLoading(btn, false);
  }
}

function fileToDataURL(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function sendChat() {
  if (!currentUserId) {
    const sel = document.getElementById('userSelect');
    currentUserId = parseInt(sel.value, 10) || null;
  }
  if (!currentUserId) return alert('Chọn hồ sơ trước');

  const text = document.getElementById('chatText').value;
  const imgFile = document.getElementById('chatImage').files[0];
  let image_data_url = null;
  if (imgFile) image_data_url = await fileToDataURL(imgFile);
  const btn = document.getElementById('btnSendChat');
  setLoading(btn, true);
  try {
    const payload = { user_id: currentUserId, text, image_data_url };
    const res = await fetch(`${apiBase}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.ok) {
      document.getElementById('answer').textContent = data.answer;
      toast('Đã nhận phản hồi', 'success');
      log('Chat success');
    } else {
      toast('Chat thất bại', 'error');
    }
  } catch (e) {
    toast('Lỗi kết nối khi chat', 'error');
  } finally {
    setLoading(btn, false);
  }
}

document.getElementById('btnReloadUsers').addEventListener('click', loadUsers);
document.getElementById('btnUseSelected').addEventListener('click', () => {
  const sel = document.getElementById('userSelect');
  const v = parseInt(sel.value, 10);
  if (!isNaN(v)) currentUserId = v;
  log(`Selected user_id=${currentUserId}`);
});
document.getElementById('btnSaveProfile').addEventListener('click', saveProfile);
document.getElementById('btnUploadPdf').addEventListener('click', uploadPdf);
document.getElementById('btnSendChat').addEventListener('click', sendChat);

// preview image
document.getElementById('chatImage').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  const preview = document.getElementById('imagePreview');
  preview.innerHTML = '';
  if (file) {
    const url = await fileToDataURL(file);
    const img = new Image();
    img.src = url;
    preview.appendChild(img);
  }
});

// init
loadUsers().catch(console.error);


