// 测试CSV解析逻辑
const testCsvParsing = () => {
  // 模拟从后端获取的CSV文件内容
  const csvText = `Review_ID;Title;Content;sentiment;强度;reason
1;Deep pockets vs. Skill;Supercell, makers of Clash of Clans, Boom Beach, Hay Day and Clash Royale seem to have a problem with Americans.;negative;-4.5;The review criticizes Supercell for catering to non-American players
2;Great game but….;I love this games so much and I've been playing it for years now.;neutral;0.0;The reviewer enjoys the game and gameplay but is frustrated with the matchmaking issues`;

  // 解析CSV数据
  const lines = csvText.trim().split('\n');
  const headers = lines[0].split(';');
  const csvData = [];
  
  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(';');
    const row = {};
    headers.forEach((header, index) => {
      row[header.trim()] = values[index] ? values[index].trim() : '';
    });
    csvData.push(row);
  }
  
  console.log('Headers:', headers.map(h => h.trim()));
  console.log('Parsed data:', csvData);
  
  // 验证数据结构
  console.log('\n=== 验证数据结构 ===');
  csvData.forEach((row, index) => {
    console.log(`Row ${index + 1}:`);
    console.log(`  Review_ID: ${row['Review_ID']}`);
    console.log(`  Title: ${row['Title']}`);
    console.log(`  Content: ${row['Content'].substring(0, 50)}...`);
    console.log(`  sentiment: ${row['sentiment']}`);
    console.log(`  强度: ${row['强度']}`);
    console.log(`  reason: ${row['reason'].substring(0, 50)}...`);
    console.log('');
  });
};

testCsvParsing(); 