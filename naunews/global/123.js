const fs = require('fs');
const path = require('path');

const sourceDir = __dirname;
const targetDir = path.join(sourceDir, 'pdf_files');

// Создаём целевую папку если её нет
if (!fs.existsSync(targetDir)) {
  fs.mkdirSync(targetDir);
}

// Читаем все файлы в текущей директории
const files = fs.readdirSync(sourceDir);

files.forEach(file => {
  const filePath = path.join(sourceDir, file);
  
  // Проверяем что это текстовый файл
  if (fs.statSync(filePath).isFile() && path.extname(file) === '.txt') {
    const content = fs.readFileSync(filePath, 'utf8');
    
    // Ищем строку с URL содержащую .pdf
    if (content.includes('URL:') && content.match(/URL:.*\.pdf/)) {
      const targetPath = path.join(targetDir, file);
      fs.renameSync(filePath, targetPath);
      console.log(`Перемещён: ${file}`);
    }
  }
});

console.log('Готово!');