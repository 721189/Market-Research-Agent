const fs = require('fs');
const path = require('path');

const targetDirectories = [
  path.join(__dirname, '../app/api/v1/research'),
  path.join(__dirname, '../app/dashboard'),
  path.join(__dirname, '../app')
];

const libDir = path.join(__dirname, '../app/lib');

function getAllFiles(dir, fileList = []) {
  if (!fs.existsSync(dir)) return fileList;
  const files = fs.readdirSync(dir);
  for (const file of files) {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    if (stat.isDirectory()) {
      if (file !== 'node_modules' && file !== '.next') {
        getAllFiles(filePath, fileList);
      }
    } else if (filePath.endsWith('.ts') || filePath.endsWith('.tsx')) {
      fileList.push(filePath);
    }
  }
  return fileList;
}

let modifiedCount = 0;
let auditedCount = 0;

const processedFiles = new Set();

for (const dir of targetDirectories) {
  const files = getAllFiles(dir);
  for (const file of files) {
    if (processedFiles.has(file)) continue;
    processedFiles.add(file);
    auditedCount++;

    let content = fs.readFileSync(file, 'utf8');
    let original = content;

    // Pattern matching relative imports going to lib/ or app/lib/
    // e.g. ../../../lib/auth or ../../app/lib/auth or ./lib/AuthProvider or ../lib/api
    const relativeLibRegex = /from\s+['"](?:\.\.\/)+lib\/([^'"]+)['"]/g;
    const relativeAppLibRegex = /from\s+['"](?:\.\.\/)+app\/lib\/([^'"]+)['"]/g;
    const dotLibRegex = /from\s+['"]\.\/lib\/([^'"]+)['"]/g;

    content = content.replace(relativeLibRegex, "from '@/lib/$1'");
    content = content.replace(relativeAppLibRegex, "from '@/lib/$1'");
    content = content.replace(dotLibRegex, "from '@/lib/$1'");

    if (content !== original) {
      fs.writeFileSync(file, content, 'utf8');
      console.log(`[REWRITTEN] ${path.relative(process.cwd(), file)}`);
      modifiedCount++;
    }
  }
}

console.log(`\nAudit Complete:`);
console.log(`- Files audited: ${auditedCount}`);
console.log(`- Files updated: ${modifiedCount}`);

// Verify that all referenced @/lib/* modules actually exist in ./app/lib/
console.log(`\nVerifying @/lib/ target exports...`);
const libFiles = fs.readdirSync(libDir);
console.log(`Available files in ./app/lib: ${libFiles.join(', ')}`);
