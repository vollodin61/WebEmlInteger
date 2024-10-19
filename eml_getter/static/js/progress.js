document.addEventListener("DOMContentLoaded", function () {
    // Получаем элементы прогресс-бара и таблицы сообщений
    const progressBar = document.getElementById('progress');
    const messagesBody = document.getElementById('messages-body');

    // Создаем WebSocket-соединение
    const socket = new WebSocket('ws://' + window.location.host + '/ws/progress/');

    // При получении сообщения через WebSocket
    socket.onmessage = function (event) {
        const data = JSON.parse(event.data);

        // Обновляем прогресс-бар
        if (data.progress) {
            progressBar.style.width = data.progress + '%';
        }

        // Добавляем сообщение в таблицу
        if (data.message) {
            const message = data.message;
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${message.subject}</td>
                <td>${message.sent_at}</td>
                <td>${message.received_at}</td>
                <td>${message.body}</td>
            `;
            messagesBody.appendChild(row);
        }
    };

    // Обрабатываем закрытие WebSocket-соединения
    socket.onclose = function (event) {
        console.log("WebSocket connection closed:", event);
    };
});
