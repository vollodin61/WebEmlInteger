var progressBar = document.getElementById('progress');
var progressText = document.getElementById('progress-text');
var messageList = document.getElementById('message-list');

var socket = new WebSocket('ws://' + window.location.host + '/ws/progress/');

socket.onmessage = function (e) {
    var data = JSON.parse(e.data);
    if (data.progress !== undefined) {
        // Обновляем прогресс-бар только если передан параметр progress
        progressBar.style.width = data.progress + '%';
    }
    if (data.status) {
        // Обновляем текст прогресса, если передан параметр status
        progressText.textContent = data.status;
    }
    if (data.new_message) {
        addMessageToTable(data.new_message);
    }
};

function addMessageToTable(message) {
    var row = document.createElement('tr');

    var idCell = document.createElement('td');
    idCell.textContent = message.id;
    row.appendChild(idCell);

    var subjectCell = document.createElement('td');
    subjectCell.textContent = message.subject;
    row.appendChild(subjectCell);

    var sendDateCell = document.createElement('td');
    sendDateCell.textContent = message.send_date;
    row.appendChild(sendDateCell);

    var receiveDateCell = document.createElement('td');
    receiveDateCell.textContent = message.receive_date;
    row.appendChild(receiveDateCell);

    var bodyCell = document.createElement('td');
    bodyCell.textContent = message.body;
    row.appendChild(bodyCell);

    messageList.appendChild(row);
}

// Обработчик для кнопки "Обновить список"
document.getElementById('refresh-button').addEventListener('click', function () {
    fetch('/refresh_messages/')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                // Очищаем таблицу сообщений
                messageList.innerHTML = '';
                progressBar.style.width = '0%';
                progressText.textContent = 'Начало обновления...';
            }
        });
});

// Обработчик для чекбокса "Показывать только новые сообщения"
document.getElementById('show-new-messages').addEventListener('change', function () {
    var showNew = this.checked;
    var url = new URL(window.location.href);
    url.searchParams.set('show_new', showNew);
    window.location.href = url.toString();
});
