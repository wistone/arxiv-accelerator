/**
 * 搜索相关函数
 */

async function searchArticles() {
    const selectedDate = document.getElementById('dateSelect').value;
    const selectedCategory = document.getElementById('categorySelect').value;
    
    if (!selectedDate) {
        showError('请选择日期');
        return;
    }

    showLoading();

    try {
        const response = await fetch('/api/search_articles', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: selectedDate,
                category: selectedCategory
            })
        });

        const data = await response.json();

        if (response.ok) {
            window.AppState.currentArticles = data.articles;
            window.AppState.hasSearched = true;
            displayArticles(data.articles);
            updateStats(data.articles);
            showSuccess(`成功加载 ${selectedDate} 的文章数据，共 ${data.total} 篇文章`);
            
            // 启用分析按钮
            document.getElementById('analyzeBtn').disabled = false;
            
            // 切换到搜索模式（标准宽度）
            setSearchMode();
            
            // 更新URL状态
            updateUrlState('search', selectedDate, selectedCategory);
        } else {
            // 如果有search_url，显示带链接的错误消息
            if (data.search_url) {
                showErrorWithLink(data.error || '搜索失败', data.search_url);
            } else {
                showError(data.error || '搜索失败');
            }
            // 禁用分析按钮
            document.getElementById('analyzeBtn').disabled = true;
            window.AppState.hasSearched = false;
        }
    } catch (error) {
        showError('网络错误，请检查服务器是否运行');
        console.error('搜索错误:', error);
        // 禁用分析按钮
        document.getElementById('analyzeBtn').disabled = true;
        window.AppState.hasSearched = false;
    }
}

function displayArticles(articles) {
    const tableBody = document.getElementById('tableBody');
    tableBody.innerHTML = '';

    // 更新表头为搜索结果格式
    const tableHead = document.querySelector('#arxivTable thead tr');
    tableHead.innerHTML = `
        <th class="number-cell">序号</th>
        <th>标题</th>
        <th class="authors-cell">作者</th>
        <th class="abstract-cell">摘要</th>
    `;

    articles.forEach(article => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="number-cell">${article.number}</td>
            <td class="title-cell">
                <div class="title-content">${article.title}</div>
                <div class="title-link">
                    <a href="${convertToPdfLink(article.link)}" target="_blank">查看链接</a>
                </div>
            </td>
            <td class="authors-cell">
                <div class="authors-content" id="authors-${article.number}">
                    ${article.authors}
                </div>
                ${article.authors.length > 100 ? `<span class="authors-toggle" onclick="toggleAuthors('authors-${article.number}')">展开/收起</span>` : ''}
            </td>
            <td class="abstract-cell">
                <div class="abstract-content" id="abstract-${article.number}">
                    ${article.abstract}
                </div>
                <span class="abstract-toggle" onclick="toggleAbstract('abstract-${article.number}')">
                    展开/收起
                </span>
            </td>
        `;
        tableBody.appendChild(row);
    });

    document.getElementById('tableContainer').style.display = 'block';
}