const cheerio = require('cheerio');
const fs = require('fs');
const path = require('path');

const dir = '/tmp/arwr-scrape';
const files = fs.readdirSync(dir).filter(f => f.startsWith('dl-'));
const results = [];

for (const file of files) {
  const html = fs.readFileSync(path.join(dir, file), 'utf-8');
  const $ = cheerio.load(html);

  // Find all table rows in download library
  $('tr').each((_, row) => {
    const $row = $(row);

    // Get date from date column
    const dateText = $row.find('.field-nir-asset-date .field__item').first().text().trim();

    // Get title and link
    const titleLink = $row.find('.field-nir-asset-title a[href*="/static-files/"]').first();
    const href = titleLink.attr('href');
    const title = titleLink.text().trim();

    // Also check for direct file links
    const fileLink = $row.find('a[href*="/static-files/"]').first();
    const fileHref = fileLink.attr('href');

    const finalHref = href || fileHref;
    const finalTitle = title || fileLink.text().trim();

    if (finalHref && finalTitle && finalTitle.length > 3) {
      const id = finalHref.replace('/static-files/', '').split('/')[0];
      const exists = results.find(r => r.id === id);
      if (!exists) {
        // Get file size
        const sizeText = $row.find('.filesize').first().text().trim();

        results.push({
          id,
          title: finalTitle,
          date: dateText || 'Unknown',
          size: sizeText,
          source: 'download-library'
        });
      }
    }
  });
}

// Sort by date
results.sort((a, b) => {
  if (a.date === 'Unknown') return 1;
  if (b.date === 'Unknown') return -1;
  return new Date(b.date) - new Date(a.date);
});

console.log('==============================================');
console.log('TOTAL FROM DOWNLOAD LIBRARY:', results.length);
console.log('==============================================');
console.log('');
console.log('ALL PRESENTATIONS:');
results.forEach((r, i) => {
  const titleShort = r.title.length > 55 ? r.title.substring(0, 55) + '...' : r.title;
  console.log((i+1) + '. [' + r.date + '] ' + titleShort + ' (' + r.size + ')');
});

console.log('');
console.log('==============================================');
console.log('COMPARISON TO HARDCODED DATA');
console.log('==============================================');
console.log('Before (hardcoded): 12 presentations');
console.log('After (scraped):    ' + results.length + ' presentations');
console.log('Improvement:        +' + (results.length - 12) + ' presentations');
