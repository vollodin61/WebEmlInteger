var progressBar = document.getElementById('progress');
var progressText = document.getElementById('progress-text');
var messageList = document.getElementById('message-list');

var socket = new WebSocket('ws://' + window.location.host + '/ws/progress/');

socket.onmessage = function(e) {
    var data = JSON.parse(e.data);
    if (data.progress) {
        progressBar.style.width = data.progress + '%';
        if (data.progress < 100) {
            progressText.textContent = 'Чтение сообщений: ' + data.progress + '%';
        } else {
            progressText.textContent = 'Получение сообщений завершено';
        }
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
