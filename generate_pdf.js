const puppeteer = require('puppeteer');

async function generatePDF(url, outputPath) {
    const browser = await puppeteer.launch({
        args: [
            '--no-sandbox', 
            '--disable-setuid-sandbox', 
            '--disable-web-security', 
            '--allow-running-insecure-content'
        ]
    });
    const page = await browser.newPage();
    console.log(`Navigating to URL: ${url}`);
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });

    // Ajuste de configuración para Letter y ajuste al ancho de la página
    await page.pdf({
        path: outputPath,
        format: 'Letter',
        printBackground: true,
        margin: {
            top: '10mm',
            bottom: '10mm',
            left: '10mm',
            right: '10mm'
        },
        scale: 1.0 // Ajusta la escala según sea necesario
    });

    await browser.close();
}

const url = process.argv[2];
const outputPath = process.argv[3];

generatePDF(url, outputPath).catch(error => {
    console.error(`Error generating PDF: ${error}`);
    process.exit(1);
});
