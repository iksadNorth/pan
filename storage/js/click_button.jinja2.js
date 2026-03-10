// 버튼 텍스트가 일부만 포함되어 있어도 클릭 (부분 일치)
// SPA 대응: 요소가 DOM에 나타날 때까지 비동기 폴링 후 클릭 (메인 스레드 블로킹 없음)
// 부모 요소 제외: 텍스트를 가진 가장 안쪽 요소만 매칭 (자손이 같은 텍스트를 가지면 제외)
var targetText = '{{ button_text or "확인" }}';
var timeoutMs = {{ timeout_ms or 10000 }};
var intervalMs = 100;
var start = Date.now();

/** 
 * 부모 요소 제외: 텍스트를 가진 가장 안쪽 요소만 매칭 (자손이 같은 텍스트를 가지면 제외)
 * @param {Element} el 요소
 * @param {string} txt 텍스트
 * @returns {boolean} 매칭 여부
 */
function isLeafMatch(el, txt) {
  var t = (el && el.innerText && el.innerText.trim()) || '';
  if (t.indexOf(txt) === -1) return false;
  var descendants = el.querySelectorAll('*');
  for (var i = 0; i < descendants.length; i++) {
    var d = (descendants[i].innerText && descendants[i].innerText.trim()) || '';
    if (d.indexOf(txt) !== -1) return false;
  }
  return true;
}

var timer = setInterval(function() {
  if (Date.now() - start > timeoutMs) {
    clearInterval(timer);
    done({ error: 'Timeout: "' + targetText + '" 버튼을 찾지 못함' });
    return;
  }
  var el = [...document.querySelectorAll('button, div, span')]
    .find(function(e) { return isLeafMatch(e, targetText); });
  if (el) {
    clearInterval(timer);
    console.log(`${Date.now() - start}ms elapsed, found ${targetText}`);
    el.click();
    done(null);
  } else {
    console.log(`${Date.now() - start}ms elapsed, still ${targetText} searching...`);
  }
}, intervalMs);
