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
using System.Configuration;
using MySql.Data.MySqlClient;  // MySQl 資料庫的 Client 端連線
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Spreadsheet;

namespace Check_Counter  // 專案名
{
    public partial class Employee : Form
    {
        private UserControlForm userControlFrom;
        private int sum = 0;  // 定義總和的值為零紀錄小計的總和
        private int money = 0;
        private int balance = 0;
        private DataTable dtProducts;  // 產品的 MySQL 資料庫
        private DataTable dtEmployees;  // 員工的 MySQL 資料庫
        private string AppDirectory = AppDomain.CurrentDomain.BaseDirectory;

        // 靜態資料保留用於對應
    
        public Employee()
        {
            InitializeComponent();
            InitalizeDataGridView();
            InitalizeFunction();
            this.Load += Employee_Load;
            txtName.Enabled = false;

            if (userControlFrom == null || userControlFrom.IsDisposed)
            {
                userControlFrom = new UserControlForm();
                // 將客戶端視窗放到第二螢幕（若有），否則放右側
                var screens = System.Windows.Forms.Screen.AllScreens;
                if (screens.Length > 1)
                    userControlFrom.Location = screens[1].WorkingArea.Location;
                else
                    userControlFrom.Location = new System.Drawing.Point(this.Right, this.Top);
            }
            userControlFrom.Show();
        }

        private void Employee_Load(object sender, EventArgs e)
        {
            bool sqlOk = false;
            try { LoadProductsFromSql("products.sql"); sqlOk = dtProducts != null && dtProducts.Rows.Count > 0; } catch { }

            if (sqlOk)
            {
                return;
            }

            bool dbOk = false;
            try { LoadProductsFromDatabase(); dbOk = dtProducts != null && dtProducts.Rows.Count > 0; } catch { }
        }

        private string GetFilePath(string fileName)
        {
            string path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, fileName);
            if (File.Exists(path)) return path;
            string projectRoot = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", ".."));
            path = Path.Combine(projectRoot, fileName);
            if (File.Exists(path)) return path;

            path = Path.Combine(projectRoot, "Resources", "data", fileName);
            if (File.Exists(path)) return path;

            path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Resources", "data", fileName);
            if (File.Exists(path)) return path;

            return Path.Combine(AppDirectory, fileName);
        }

        private void InitalizeFunction()
        {
            dataGridView2.Columns.Clear();
            //dataGridView2.Columns.Add("No", "項次");
            //dataGridView2.Columns.Add("Function Name", "功能名稱");
            dataGridView2.Columns.Add("", "");
            dataGridView2.Columns.Add("", "");
            dataGridView2.Columns.Add("", "");
            dataGridView2.Columns.Add("", "");
            dataGridView2.RowTemplate.Height = 60;
            dataGridView2.Rows.Add("7", "8", "9", "←");
            dataGridView2.Rows.Add("4", "5", "6", "清除");
            dataGridView2.Rows.Add("1", "2", "3", "");
            dataGridView2.Rows.Add("0", "00", "", "");
            dataGridView2.Rows.Add("0", "00", "", "結帳");
        }
        // 產品資料庫讀取
        private void LoadProductsFromSql(string fileName)
        {
            string safePath = GetFilePath(fileName);
            if (!File.Exists(safePath)) throw new FileNotFoundException(safePath);

            dtProducts = new DataTable();
            dtProducts.Columns.Add("Barcode");
            dtProducts.Columns.Add("ProductName");
            dtProducts.Columns.Add("Price", typeof(int));
            dtProducts.Columns.Add("Stock", typeof(int));
            dtProducts.Columns.Add("Shelves");

            foreach (string line in File.ReadLines(safePath, Encoding.UTF8))
            {
                string trimmed = line.TrimStart();
                if (!trimmed.StartsWith("INSERT INTO", StringComparison.OrdinalIgnoreCase)) continue;

                int start = trimmed.IndexOf("VALUES (", StringComparison.OrdinalIgnoreCase);
                if (start < 0) continue;
                start += 8;
                int end = trimmed.LastIndexOf(");");
                if (end < 0) continue;

                var vals = ParseSqlValues(trimmed.Substring(start, end - start));
                if (vals.Count < 5) continue;

                int price = 0; int.TryParse(vals[2], out price);
                int stock = 0; int.TryParse(vals[3], out stock);
                dtProducts.Rows.Add(vals[0], vals[1], price, stock, vals[4]);
            }
        }

        private System.Collections.Generic.List<string> ParseSqlValues(string valuesPart)
        {
            var result = new System.Collections.Generic.List<string>();
            var current = new StringBuilder();
            bool inQuote = false;

            for (int i = 0; i < valuesPart.Length; i++)
            {
                char c = valuesPart[i];
                if (c == '\'' && (i == 0 || valuesPart[i - 1] != '\\'))
                {
                    inQuote = !inQuote;
                }
                else if (c == ',' && !inQuote)
                {
                    result.Add(current.ToString().Trim());
                    current.Clear();
                }
                else
                {
                    current.Append(c);
                }
            }
            if (current.Length > 0)
                result.Add(current.ToString().Trim());

            return result;
        }
        
        private void LoadProductsFromDatabase()
        {
            string connStr = ConfigurationManager.ConnectionStrings["CheckCounterDB"].ConnectionString;

            dtProducts = new DataTable();
            dtProducts.Columns.Add("Barcode");
            dtProducts.Columns.Add("ProductName");
            dtProducts.Columns.Add("Price", typeof(int));
            dtProducts.Columns.Add("Stock", typeof(int));
            dtProducts.Columns.Add("Shelves");

            using (MySqlConnection conn = new MySqlConnection(connStr))
            {
                conn.Open();
                string sql = "SELECT barcode, product_name, price, stock, shelves FROM products";
                using (MySqlCommand cmd = new MySqlCommand(sql, conn))
                using (MySqlDataReader reader = cmd.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        string barcode = reader["barcode"].ToString();
                        string name = reader["product_name"].ToString();
                        int price = Convert.ToInt32(reader["price"]);
                        int stock = Convert.ToInt32(reader["stock"]);
                        string shelf = reader["shelves"].ToString();

                        dtProducts.Rows.Add(barcode, name, price, stock, shelf);
                    }
                }
            }
        }
        
        private void InitalizeDataGridView()
        {
            dataGridView1.Columns.Clear();
            dataGridView1.Columns.Add("Barcode",        "條碼");
            dataGridView1.Columns.Add("ProductName",    "商品名稱");
            dataGridView1.Columns.Add("Price",          "價格");
            dataGridView1.Columns.Add("Quantity",       "數量");
            dataGridView1.Columns.Add("AgeRestriction", "年齡限制");

            var btnDelete = new DataGridViewButtonColumn();
            btnDelete.Name    = "DeleteBtn";
            btnDelete.HeaderText = "操作";
            btnDelete.Text    = "刪除";
            btnDelete.UseColumnTextForButtonValue = true;
            dataGridView1.Columns.Add(btnDelete);

            dataGridView1.CellClick += dataGridView1_DeleteClick;
        }

        private void dataGridView1_DeleteClick(object sender, DataGridViewCellEventArgs e)
        {
            if (e.RowIndex < 0) return;
            if (dataGridView1.Columns[e.ColumnIndex].Name != "DeleteBtn") return;

            DataGridViewRow row = dataGridView1.Rows[e.RowIndex];
            if (int.TryParse(row.Cells["Price"].Value?.ToString(), out int price))
            {
                sum -= price;
                if (sum < 0) sum = 0;
                lblSum.Text = "總金額:" + sum + "元";
            }

            dataGridView1.Rows.RemoveAt(e.RowIndex);
            SyncWithUserControl();
        }

        private void AddProductToGrid(string barcode)
        {
            if (dtProducts == null)
            {
                MessageBox.Show("商品資料尚未載入", "錯誤");
                return;
            }

            foreach (DataRow row in dtProducts.Rows)
            {
                if (row["Barcode"].ToString().Trim() == barcode.Trim())
                {
                    int price = Convert.ToInt32(row["Price"]);
                    string productName = row["ProductName"].ToString();
                    dataGridView1.Rows.Add(barcode.Trim(), productName, price, 1, "無");
                    sum += price;
                    lblSum.Text = "總金額:" + sum + "元";
                    RecordSaleToExcel(barcode.Trim(), productName, price);
                    SyncWithUserControl();
                    return;
                }
            }

            MessageBox.Show("找不到條碼：" + barcode, "查無商品");
        }

        private void RecordSaleToExcel(string barcode, string productName, int price)
        {
            string filePath = Path.Combine(AppDirectory, "sales_" + DateTime.Now.ToString("yyyyMMdd") + ".xlsx");
            try
            {
                if (!File.Exists(filePath))
                    CreateSalesExcel(filePath);
                AppendSaleRow(filePath, barcode, productName, price);
            }
            catch { }
        }

        private void CreateSalesExcel(string filePath)
        {
            using (var doc = SpreadsheetDocument.Create(filePath, SpreadsheetDocumentType.Workbook))
            {
                var wbPart = doc.AddWorkbookPart();
                wbPart.Workbook = new Workbook();
                var wsPart = wbPart.AddNewPart<WorksheetPart>();
                var sheetData = new SheetData();
                wsPart.Worksheet = new Worksheet(sheetData);
                var sheets = wbPart.Workbook.AppendChild(new Sheets());
                sheets.Append(new Sheet() { Id = wbPart.GetIdOfPart(wsPart), SheetId = 1, Name = "銷售記錄" });

                var header = new Row() { RowIndex = 1 };
                string[] cols = { "日期", "時間", "條碼", "商品名稱", "價格" };
                for (uint i = 0; i < cols.Length; i++)
                    header.Append(MakeCell(cols[i], i + 1, 1));
                sheetData.Append(header);
                wbPart.Workbook.Save();
            }
        }

        private void AppendSaleRow(string filePath, string barcode, string productName, int price)
        {
            using (var doc = SpreadsheetDocument.Open(filePath, true))
            {
                var wsPart = doc.WorkbookPart.WorksheetParts.First();
                var sheetData = wsPart.Worksheet.GetFirstChild<SheetData>();
                uint rowIdx = (uint)(sheetData.Elements<Row>().Count() + 1);
                var dataRow = new Row() { RowIndex = rowIdx };
                string[] vals = {
                    DateTime.Now.ToString("yyyy/MM/dd"),
                    DateTime.Now.ToString("HH:mm:ss"),
                    barcode,
                    productName,
                    price.ToString()
                };
                for (uint i = 0; i < vals.Length; i++)
                    dataRow.Append(MakeCell(vals[i], i + 1, rowIdx));
                sheetData.Append(dataRow);
                wsPart.Worksheet.Save();
            }
        }

        private Cell MakeCell(string value, uint col, uint row)
        {
            string colName = "";
            uint c = col;
            while (c > 0) { colName = (char)('A' + (c - 1) % 26) + colName; c = (c - 1) / 26; }
            return new Cell()
            {
                CellReference = colName + row,
                DataType = CellValues.InlineString,
                InlineString = new InlineString(new Text(value))
            };
        }
        
        private void SyncWithUserControl()
        {
            if (userControlFrom != null)
            {
                userControlFrom.ClearGrid();
                foreach (DataGridViewRow row in dataGridView1.Rows)
                {
                    if (row.IsNewRow) continue;
                    userControlFrom.AddProductToGrid(row.Cells[1].Value?.ToString(), row.Cells[3].Value?.ToString(), row.Cells[2].Value?.ToString(), row.Cells[2].Value?.ToString());
                }
                userControlFrom.UpdateTotal(sum.ToString());
                userControlFrom.UpdateGive(balance.ToString());
            }
            
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

        private void txtBarcode_GotFocus(object sender, EventArgs e)
        {
            if (txtBarcode.ForeColor == System.Drawing.Color.Gray)
            {
                txtBarcode.Text = "";
                txtBarcode.ForeColor = System.Drawing.Color.Black;
            }
        }

        private void txtBarcode_KeyPress(object sender, KeyPressEventArgs e)
        {
            if (e.KeyChar == (char)Keys.Enter || e.KeyChar == (char)10)
            {
                e.Handled = true;
                string raw = txtBarcode.Text;
                string input = new string(raw.Where(c => c >= '0' && c <= '9').ToArray());
                if (!string.IsNullOrEmpty(input))
                    AddProductToGrid(input);
                txtBarcode.Text = "";
                txtBarcode.ForeColor = System.Drawing.Color.Gray;
            }
        }

        private void btnProducts_Click(object sender, EventArgs e)
        {
            if (dtProducts == null || dtProducts.Rows.Count == 0)
            {
                MessageBox.Show("尚無商品資料", "提示");
                return;
            }

            dataGridView1.Rows.Clear();
            dataGridView1.Columns.Clear();
            dataGridView1.Columns.Add("Barcode",     "條碼");
            dataGridView1.Columns.Add("ProductName", "商品名稱");
            dataGridView1.Columns.Add("Price",       "價格");
            dataGridView1.Columns.Add("Stock",       "庫存");
            dataGridView1.Columns.Add("Shelves",     "貨架");

            foreach (DataRow row in dtProducts.Rows)
            {
                dataGridView1.Rows.Add(
                    row["Barcode"].ToString(),
                    row["ProductName"].ToString(),
                    row["Price"].ToString(),
                    row["Stock"].ToString(),
                    row["Shelves"].ToString()
                );
            }

            MessageBox.Show("已載入 " + dtProducts.Rows.Count + " 筆商品（檢視用）\n關閉此視窗後請重新整理清單以繼續結帳", "商品報表");

            // 還原為結帳用欄位
            dataGridView1.Rows.Clear();
            dataGridView1.Columns.Clear();
            dataGridView1.Columns.Add("Barcode",        "條碼");
            dataGridView1.Columns.Add("ProductName",    "商品名稱");
            dataGridView1.Columns.Add("Price",          "價格");
            dataGridView1.Columns.Add("Quantity",       "數量");
            dataGridView1.Columns.Add("AgeRestriction", "年齡限制");
            sum = 0;
            lblSum.Text = "總金額:0元";
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
            dataGridView2.Rows.Add("7", "投庫");

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


        private void btnLogin_Click(object sender, EventArgs e)
        {
            if (txtAccount.Text == "624826" && txtPassword.Text == "684262")
            {
                MessageBox.Show("登入成功", "成功");
            }
            else
            {
                MessageBox.Show("登入失敗", "失敗");
            }
        }

        private void txtMoney_Click(object sender, EventArgs e)
        {
            if (txtMoney.ForeColor == System.Drawing.Color.Gray)
            {
                txtMoney.Text = "";
                txtMoney.ForeColor = System.Drawing.Color.Black;
            }
            ShowNumpad();
        }

        private void ShowNumpad()
        {
            dataGridView2.CellClick -= dataGridView2_NumpadClick;
            dataGridView2.Rows.Clear();
            dataGridView2.Columns.Clear();

            for (int i = 0; i < 3; i++)
            {
                var col = new DataGridViewButtonColumn();
                col.UseColumnTextForButtonValue = false;
                col.Name        = "NumCol" + i;
                col.HeaderText  = "";
                col.AutoSizeMode = DataGridViewAutoSizeColumnMode.Fill;
                dataGridView2.Columns.Add(col);
            }

            

            dataGridView2.CellClick += dataGridView2_NumpadClick;
        }

        private void dataGridView2_NumpadClick(object sender, DataGridViewCellEventArgs e)
        {
            if (e.RowIndex < 0) return;
            string val = dataGridView2.Rows[e.RowIndex].Cells[e.ColumnIndex].Value?.ToString();
            if (string.IsNullOrEmpty(val)) return;

            if (val == "←")
            {
                if (txtMoney.Text.Length > 0)
                    txtMoney.Text = txtMoney.Text.Substring(0, txtMoney.Text.Length - 1);
            }
            else if (val == "清除")
            {
                txtMoney.Text = "";
            }
            else
            {
                txtMoney.Text += val;
            }
        }

        private void txtMoney_KeyPress(object sender, KeyPressEventArgs e)
        {
            if (e.KeyChar == (char)Keys.Enter)
            {
                e.Handled = true;
                int.TryParse(txtMoney.Text, out money);
                balance = money - sum;
                lblBalance.Text = "找:" + balance + "元";
                txtMoney.Text = "";
                dataGridView1.Rows.Clear();
                txtMoney.ForeColor = System.Drawing.Color.Gray;
                SyncWithUserControl();
            }
        }
    }
}
