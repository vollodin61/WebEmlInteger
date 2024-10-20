var progressBar = document.getElementById('progress');
var progressText = document.getElementById('progress-text');

var socket = new WebSocket('ws://' + window.location.host + '/ws/progress/');

socket.onmessage = function(e) {
    var data = JSON.parse(e.data);
    if (data.progress) {
        progressBar.style.width = data.progress + '%';
        if (data.progress < 100) {
            progressText.textContent = 'Чтение сообщений: ' + data.progress + '%';
        } else {
            progressText.textContent = 'Получение сообщений завершено';
            // Перезагрузка страницы для обновления списка сообщений
            setTimeout(function() {
                location.reload();
            }, 1000);
        }
    }
};
