async function HomePage(){
  const { create } = window.__APP__;
  const wrap = create('div','page-grid');

  const card = create('section','card');
  card.innerHTML = `
    <h2 class="card-title">Chào mừng</h2>
    <div class="note">Ứng dụng tư vấn thực phẩm dựa trên hồ sơ sức khoẻ. Hãy tạo hồ sơ trong mục "Hồ sơ", upload hồ sơ PDF trong "Tài liệu" và bắt đầu trò chuyện tại "Chat".</div>
  `;
  wrap.appendChild(card);
  return wrap;
}

window.__APP__.HomePage = HomePage;
window.__APP__.route = window.__APP__.route || function(){};
// register route
(function register(){
  const routes = window.__APP__.routes || {};
})();
// minimal route binding
window.addEventListener('load', ()=>{ window.__APP__.route && window.__APP__.route('/', HomePage); });


