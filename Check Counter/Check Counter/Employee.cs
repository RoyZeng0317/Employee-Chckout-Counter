using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Media;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.IO;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Spreadsheet;

namespace Check_Counter
{
    public partial class Employee : Form
    {
        //private UserControlForm userControlFrom;
        private int sum = 0;
        private DataTable dtProducts;
        private string AppDirectory = AppDomain.CurrentDomain.BaseDirectory;

        // 靜態資料保留用於對應
        
        
        
        public Employee()
        {
            InitializeComponent();
            InitalizeDataGridView();
            InitalizeFunction();
            LoadProductsFromExcel("product.xlsx");
            txtName.Enabled = false;
        }

        private string GetFilePath(string fileName)
        {
            string path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, fileName);
            if (File.Exists(path)) return path;
            string projectRoot = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", ".."));
            path = Path.Combine(projectRoot, fileName);
            if (File.Exists(path)) return path;
            
            // 嘗試從 Resources/data 讀取
            path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Resources", "data", fileName);
            if (File.Exists(path)) return path;

            return Path.Combine(AppDirectory, fileName);
        }

        private void InitalizeFunction()
        {
            dataGridView2.Columns.Clear();
            dataGridView2.Columns.Add("No", "項次");
            dataGridView2.Columns.Add("Function Name", "功能名稱");
        }



        private void LoadProductsFromExcel(string fileName)
        {
            string safePath = GetFilePath(fileName);
            if (!File.Exists(safePath)) return;

            dtProducts = new DataTable();
            dtProducts.Columns.Add("Barcode");
            dtProducts.Columns.Add("ProductName");
            dtProducts.Columns.Add("Price", typeof(int));
            dtProducts.Columns.Add("Stock", typeof(int));
            dtProducts.Columns.Add("Shelves");

            try
            {
                using (SpreadsheetDocument doc = SpreadsheetDocument.Open(safePath, false))
                {
                    WorkbookPart workbookPart = doc.WorkbookPart;
                    Sheet sheet = workbookPart.Workbook.Descendants<Sheet>().FirstOrDefault();
                    if (sheet == null) return;

                    WorksheetPart worksheetPart = (WorksheetPart)workbookPart.GetPartById(sheet.Id);
                    SheetData sheetData = worksheetPart.Worksheet.Elements<SheetData>().First();
                    var rows = sheetData.Elements<Row>().ToList();

                    foreach (Row row in rows.Skip(1)) // 跳過標題列
                    {
                        var cells = row.Elements<Cell>().ToList();
                        if (cells.Count < 2) continue;

                        string barcode = GetCellValue(doc, GetCellByColumn(cells, "A", row.RowIndex));
                        string name = GetCellValue(doc, GetCellByColumn(cells, "B", row.RowIndex));
                        string priceStr = GetCellValue(doc, GetCellByColumn(cells, "C", row.RowIndex));
                        string stockStr = GetCellValue(doc, GetCellByColumn(cells, "D", row.RowIndex));
                        string shelf = GetCellValue(doc, GetCellByColumn(cells, "E", row.RowIndex));

                        if (string.IsNullOrEmpty(name)) continue;

                        int price = 0; int.TryParse(priceStr, out price);
                        int stock = 0; int.TryParse(stockStr, out stock);

                        dtProducts.Rows.Add(barcode, name, price, stock, shelf);
                    }
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("讀取 Excel 失敗: " + ex.Message);
            }
        }

        private Cell GetCellByColumn(List<Cell> cells, string columnName, uint rowIndex)
        {
            string cellReference = columnName + rowIndex;
            return cells.FirstOrDefault(c => c.CellReference == cellReference);
        }

        private string GetCellValue(SpreadsheetDocument doc, Cell cell)
        {
            if (cell == null || cell.CellValue == null) return "";
            string value = cell.CellValue.InnerText;

            if (cell.DataType != null && cell.DataType.Value == CellValues.SharedString)
            {
                return doc.WorkbookPart.SharedStringTablePart.SharedStringTable.ChildElements[int.Parse(value)].InnerText;
            }
            return value;
        }

        private void InitalizeDataGridView()
        {
            dataGridView1.Columns.Clear();
            dataGridView1.Columns.Add("Barcode", "條碼");
            dataGridView1.Columns.Add("ProductName", "商品名稱");
            dataGridView1.Columns.Add("Price", "價格");
            dataGridView1.Columns.Add("Quantity", "數量");
            dataGridView1.Columns.Add("AgeRestriction", "年齡限制");
        }

        private void AddProductToGrid(string barcode)
        {
            if (dtProducts == null) return;
            foreach (DataRow row in dtProducts.Rows)
            {
                if (row["Barcode"].ToString() == barcode)
                {
                    int price = Convert.ToInt32(row["Price"]);
                    dataGridView1.Rows.Add(barcode, row["ProductName"], price, 1, "無");
                    sum += price;
                    lblSum.Text = "總金額:" + sum + "元";
                    SyncWithUserControl();
                    break;
                }
            }
        }

        private void SyncWithUserControl()
        {/*
            if (userControlFrom != null)
            {
                userControlFrom.ClearGrid();
                foreach (DataGridViewRow row in dataGridView1.Rows)
                {
                    if (row.IsNewRow) continue;
                    userControlFrom.AddProductToGrid(row.Cells[1].Value?.ToString(), row.Cells[3].Value?.ToString(), row.Cells[2].Value?.ToString(), row.Cells[2].Value?.ToString());
                }
                userControlFrom.UpdateTotal(sum.ToString());
            }
            */
        }

        private void txtAccount_Click(object sender, EventArgs e)
        {
            txtAccount.Text = "";
            txtAccount.ForeColor = System.Drawing.Color.Black;
        }

        private void txtPassword_Click(object sender, EventArgs e)
        {
            txtPassword.Text = "";
            txtPassword.ForeColor = System.Drawing.Color.Black;
        }

        private void txtBarcode_KeyPress(object sender, KeyPressEventArgs e)
        {
            if (e.KeyChar == (char)Keys.Enter)
            {
                e.Handled = true;
                AddProductToGrid(txtBarcode.Text);
                txtBarcode.Clear();
            }
        }

        private void txtFunction_Click(object sender, EventArgs e)
        {
            dataGridView2.Rows.Clear();
            dataGridView2.Rows.Add("1", "咖啡機台");
            dataGridView2.Rows.Add("2", "熱狗機");
            dataGridView2.Rows.Add("3", "包子機");
            dataGridView2.Rows.Add("4", "影印機");
            dataGridView2.Rows.Add("5", "溫罐機器");
            dataGridView2.Rows.Add("6", "交班");

            if (dataGridView2.Columns.Count <= 2)
            {
                DataGridViewButtonColumn btnDisplay = new DataGridViewButtonColumn();
                btnDisplay.Name = "顯示";
                btnDisplay.Text = "顯示";
                btnDisplay.UseColumnTextForButtonValue = true;
                dataGridView2.Columns.Add(btnDisplay);
                dataGridView2.CellClick += dataGridView1_CellClick;
            }
            
            dataGridView1.Columns.Clear();
            dataGridView1.Columns.Add("Barcode", "條碼");
            dataGridView1.Columns.Add("ProductName", "商品名稱");
            dataGridView1.Columns.Add("Price", "價格");
            dataGridView1.Columns.Add("Quantity", "數量");
            dataGridView1.Columns.Add("AgeRestriction", "年齡限制");

        }
        
        private void dataGridView1_CellClick(object sender, DataGridViewCellEventArgs e)
        {
            if (e.RowIndex < 0) return;
            string functionNo = dataGridView2.Rows[e.RowIndex].Cells[0].Value?.ToString();
            string functionName = dataGridView2.Rows[e.RowIndex].Cells[1].Value?.ToString();

            switch (functionNo)
            {
                case "1":
                case "2":
                case "3":
                case "4":
                case "5":
                    AddProductsByShelf(functionName);
                    break;
                case "6":
                    MessageBox.Show("交班功能尚未實作");
                    break;
            }
            
        }

        private void AddProductsByShelf(string shelfName)
        {
            if (dtProducts == null) return;
            foreach (DataRow row in dtProducts.Rows)
            {
                if (row["Shelves"].ToString().Trim() == shelfName)
                {
                    string barcode = row["Barcode"].ToString();
                    string name = row["ProductName"].ToString();
                    int price = Convert.ToInt32(row["Price"]);
                    
                    dataGridView1.Rows.Add(barcode, name, price, 1, "無");
                    
                    sum += price;
                    lblSum.Text = "總金額:" + sum + "元";
                }
            }
            SyncWithUserControl();
        }
    }
}
