# Rekap Perubahan Modul `it_helpdesk_v2`

**Tanggal Rekap Terbaru:** 16 Oktober 2026  
**Referensi Commit Terakhir (GitHub):** `43f2b2e feat: decouple ticket publish and auto-routing, update tab container and 11-column list view`  
**Repository GitHub:** `https://github.com/miqiqbal/addons_iian.git` (Branch: `main`)  
**Status:** All Changes Committed & Pushed to GitHub (`colab/main`)

---

## 📌 Ringkasan Utama Perubahan

Pembaruan pada modul **`it_helpdesk_v2`** berfokus pada **18 area utama**:

1. **Master Data Fitur Baru: CR Type (`helpdesk.cr.type`)**.
2. **Perombakan Workflow Approval Change Request Multi-Tier (5-Level Flow)**.
3. **Integrasi & Auto-Sync Otomatis User (`res.users`) ➔ Employee (`hr.employee`)**.
4. **Ekstensi Struktur Organisasi HR & Penataan Form Employee**.
5. **Dynamic Filtering pada Keyword Routing Rules (`helpdesk.keyword`)**.
6. **Penyesuaian Hak Akses & Peran Pengguna (Group & Security Access)**.
7. **Automated Unit Testing Suite**.
8. **Pembaruan Pengirim Email Notifikasi (`system.itd@hkinfrastruktur.com`)**.
9. **Filter Departemen Target & Penentuan Kadept BPO Berdasarkan Jabatan**.
10. **Pop-Up Wizard Reject Change Request & Pengembalian ke Status Draft**.
11. **Pengiriman Email Langsung & Auto Sync Mail Template**.
12. **Pembatasan Akses Edit Form & Tombol Action Role Employee (Draft Only & Reject Past Draft)**.
13. **Audit Logika Tiket, Auto-Routing, & Perhitungan SLA Response**.
14. **Matriks Lengkap Hak Akses Pengguna Login (Menu, Tombol, & Kontrol Edit)**.
15. **Evolusi Struktur Role Pengguna & Keamanan Penugasan Tiket (Assigned Ticket to)**.
16. **Pemisahan (Decoupling) Auto-Routing dari Tombol Publish Tiket (Manual / Dedicated Escalation Flow)**.
17. **Restrukturisasi Tab Container: Penggantian Tab Description Menjadi Tab "Expected Result & Link"**.
18. **Restrukturisasi Tree/List View Tiket (11 Kolom Laporan Kendala & Base UX Optimization)**.

---

## 🛠️ Detail Perubahan per Komponen

### 1. Integrasi & Auto-Sync User (`res.users`) ➔ Employee (`hr.employee`)
* **Auto-Sync pada User Creation/Write (`models/res_users.py`)**:
  * Menambahkan method `_sync_hr_employee()` pada penambahan/pengubahan User di menu *IT Helpdesk Configuration ➔ Users*.
  * Setiap User baru secara otomatis dibuatkan atau dihubungkan ke record `hr.employee` terkait (`user_id = user.id`).
* **Auto-Link pada Employee Creation (`models/hr_employee.py`)**:
  * Saat Karyawan baru dibuat di modul *Employee*, sistem secara otomatis mencari `res.users` berdasarkan Email / Nama dan memasang `user_id` secara otomatis.
* **Migrasi Massal & Hook Deployment (`hooks.py`)**:
  * Menambahkan `sync_all_users_to_employees(env)` pada `post_init_hook`.
  * Telah mengeksekusi migrasi massal seluruh **744 data User** yang ada di database ke profil `hr.employee`.
* **Smart Resolution pada Change Request (`models/helpdesk_change_request.py`)**:
  * Menambahkan method `_get_employee_for_user(user)` yang mencari data Employee dari User login secara bertahap (*user_id*, Email, Nama) dan melakukan *auto-link* secara otomatis jika belum terhubung.
  * Menjamin alur approval Change Request berjalan stabil meskipun field manager pada Employee masih kosong (dibiarkan kosong untuk diisi manual oleh admin).

---

### 2. Ekstensi HR & Penataan Form View Employee (`views/hr_employee_views.xml`)
* **Penambahan Field Hirarki (`models/hr_employee.py`)**:
  * Menambahkan field `kadept_id` (*Head of Placement / Kepala Dept.*) dan `indirect_manager_id` (*Indirect Manager*) pada `hr.employee` dan `hr.department`.
* **Penyesuaian String Label & Urutan Form View (`views/hr_employee_views.xml`)**:
  * Menyesuaikan label `parent_id` menjadi **`Direct Manager`**.
  * Menyesuaikan label `kadept_id` menjadi **`Head of Placement / Kepala Dept.`**.
  * Menata urutan field pada kelompok kanan Form Employee:
    1. **Department**
    2. **Head of Placement / Kepala Dept.**
    3. **Indirect Manager**
    4. **Direct Manager**
    5. **Coach**

---

### 3. Penyempurnaan Dynamic Filtering pada Keyword Routing Rules (`helpdesk.keyword`)
* **Dynamic Filter Kategori & Sub Kategori (`models/helpdesk_keyword.py` & `views/helpdesk_keyword_views.xml`)**:
  * Menambahkan `@api.onchange('service_ids')` untuk menyaring pilihan Kategori Target (`category_ids`) agar hanya menampilkan kategori yang termasuk dalam Service Catalog yang dipilih.
  * Menambahkan `@api.onchange('category_ids')` dan domain XML `[('category_id', 'in', category_ids)]` untuk menyaring pilihan Sub Kategori Target (`subcategory_ids`) agar hanya menampilkan subkategori yang merupakan turunan dari Kategori yang dipilih.
* **PIC IT Auto Assign (Urutan Prioritas)**:
  * Menggunakan susunan urutan *drag-and-drop* (`sequence widget="handle"`) pada `engineer_line_ids` yang terhubung ke akun User/Engineer.

---

### 4. Master Data Fitur Baru: CR Type (`helpdesk.cr.type`)
* **Model Baru (`models/helpdesk_cr_type.py`)**:
  * Dibuat model `helpdesk.cr.type` dengan atribut `name`, `code`, `description`, `active`, dan `sequence`.
  * Ditambahkan relasi `cr_type_id` (Many2one ke `helpdesk.cr.type`) pada model `helpdesk.change.request`.
* **Views & Manifest (`views/helpdesk_cr_type_views.xml`)**:
  * Dibuat tampilan *Tree*, *Form*, *Search*, dan *Action* untuk pengolahan master data CR Type.

---

### 5. Perombakan Workflow Approval Multi-Tier (5-Level Approval Flow)
* **Restrukturisasi Status Change Request**:
  * `draft` ➔ **Draft**
  * `dept_mgr_approval` ➔ **Approval Manager Dept Terkait**
  * `kadept_approval` ➔ **Approval Kadept Terkait**
  * `bpo_approval` ➔ **Approval Kadept BPO** *(otomatis di-bypass jika departemen tujuan adalah IT)*
  * `it_mgr_review` ➔ **Review Manager IT** *(Penetapan Engineer/PIC IT & Estimasi Tanggal Penyelesaian)*
  * `it_kadept_approval` ➔ **Approval Final Kepala Departemen IT**
  * `in_progress` ➔ **In Progress (Engineering Queue)**
  * `done` ➔ **Done**
  * `closed` ➔ **Closed**
  * `rejected` ➔ **Rejected**
* **Dynamic Approver Resolution**:
  * Menambahkan helper methods (`_get_dept_manager_user`, `_get_kadept_manager_user`, `_get_bpo_kadept_manager_user`, `_default_manager_it`, `_default_kadept_it_manager`) untuk menentukan pejabat pengesah secara otomatis berdasarkan hirarki karyawan/departemen.
* **Fitur Reopen Ke Progress**:
  * Menambahkan metode `action_reopen_progress()` untuk mengembalikan CR berstatus `done` / `closed` kembali ke antrean `in_progress`.

---

### 6. Penyesuaian Hak Akses & Peran (Security & Access Rights)
* **Grup & Hierarki Hak Akses (`security/helpdesk_security.xml`)**:
  * `group_helpdesk_user`: **Employee** (Otomatis diwarisi oleh semua pengguna internal Odoo `base.group_user`).
  * `group_helpdesk_agent`: **Manager Dept.** (Approval CR Dept & Monitoring progres).
  * `group_helpdesk_it_manager`: **IT Manager** (Approval CR level IT & Analitik Dashboard).
  * `group_helpdesk_manager`: **IT Admin** (Akses penuh administrator & konfigurasi master).
* **Record Rules**:
  * Memperbarui aturan baca/tulis CR (`rule_helpdesk_change_request_base_user` & `rule_helpdesk_change_request_employee`) agar mencakup seluruh pejabat pengesah (Requester, Manager Dept, Kadept Terkait, Kadept BPO, Manager IT, Kadept IT, dan Engineer).
* **Access Control List (`security/ir.model.access.csv`)**:
  * Menambahkan izin akses read/write/create/delete untuk model `helpdesk.cr.type`.

---

### 7. Pembaruan Menu Navigator & Unit Test
* **Menu Navigator (`views/helpdesk_menus.xml`)**:
  * Mengatur `custom_parent_id` ke ID menu `882`.
  * Membatasi akses menu utama (*Dashboard*, *All Ticket*, *Reports*, *Configuration*) agar sesuai dengan peran `IT Manager` dan `IT Admin`.
  * Menambahkan sub-menu *Configuration -> CR Type*.
* **Automated Unit Testing (`tests/test_helpdesk_change_request_email.py`)**:
  * Pengujian alur persetujuan 5-level (`test_approve_flow_standard`) dan bypass BPO (`test_approve_flow_bypass_bpo_for_it_dept`).

---

### 8. Pembaruan Pengirim Email Notifikasi (`system.itd@hkinfrastruktur.com`)
* **Penggantian Email Sender pada Template Mail (`data/`)**:
  * Memperbarui seluruh field `email_from` di 11 record `mail.template` dari email lama (`rahmadana908@gmail.com`) menjadi email resmi perusahaan: **`system.itd@hkinfrastruktur.com`**.
  * Berlaku pada template notifikasi Ticket Created, Ticket Assigned, SLA Warning 80%, SLA Breach, Ticket Resolved, serta seluruh Notifikasi CR Approval (Dept Manager, IT Manager, CR Rejected, dan CR Done).

---

### 9. Filter Departemen Target & Penentuan Kadept BPO Berdasarkan Jabatan
* **Filter `target_department_id` (`models/helpdesk_change_request.py`)**:
  * Menambahkan domain filter `[('name', '=ilike', 'Departemen %')]` pada pilihan *CR to Departement* agar hanya menampilkan departemen operasional.
* **Smart Matching Kadept BPO (`_get_bpo_kadept_manager_user`)**:
  * Memperbarui logika pencarian Kadept BPO agar mencocokkan karyawan dengan nama jabatan `Kepala [Nama Departemen Target]` (contoh: *Kepala Departemen Human Capital*) secara presisi.

---

### 10. Pop-Up Wizard Reject Change Request & Pengembalian ke Status Draft
* **Wizard Reject CR (`wizard/helpdesk_cr_reject_wizard.py` & `views.xml`)**:
  * Menambahkan pop-up dialog penolakan Change Request yang mewajibkan Approver mengisikan alasan penolakan / catatan revisi.
  * Saat dikonfirmasi, status CR secara otomatis **dikembalikan ke status `Draft`** dan nomor antrian di-reset, sehingga pemohon dapat merevisi dan mengajukan kembali.
* **Banner Peringatan Revisi (`views/helpdesk_change_request_views.xml`)**:
  * Menambahkan banner peringatan berwarna kuning (Warning Alert) di bagian atas form view saat status `Draft` yang menampilkan catatan penolakan sebelumnya.

---

### 11. Pengiriman Email Langsung & Auto Sync Mail Template
* **Perubahan Parameter `force_send=True` (`models/helpdesk_ticket.py`)**:
  * Mengubah `force_send=False` menjadi `force_send=True` pada pengiriman email notifikasi tiket baru dan SLA breach agar email langsung dikirimkan detik itu juga via SMTP tanpa tertahan di antrian outbox Odoo.
* **Auto-Update SQL pada Module Upgrade (`models/helpdesk_ticket.py`)**:
  * Menambahkan eksekusi SQL pada method `init()` untuk otomatis mengubah `noupdate = False` pada `ir_model_data` dan memperbarui seluruh template email ke `system.itd@hkinfrastruktur.com`.

---

### 12. Pembatasan Akses Edit Form & Tombol Action Role Employee (Draft Only & Reject Past Draft)
* **Akses Edit Form HANYA pada State `Draft`**:
  * Pada form view Ticket (`helpdesk.ticket`) dan Change Request (`helpdesk.change_request`), seluruh field input diatur menjadi `readonly` apabila status record **bukan `Draft`**.
  * Pengguna dengan role **Employee** (`group_helpdesk_user`) hanya dapat melakukan pengubahan data saat record berada pada status **Draft**.
* **Proteksi Python `write()`**:
  * Menambahkan validasi pada metode `write()` di model `helpdesk.ticket` dan `helpdesk.change_request` untuk mencegah penulisan langsung oleh role Employee pada status beranjak dari Draft (mencegah manipulasi data dari API/UI non-draft).
* **Tombol Action pada Header Form**:
  * Pada status **Draft**, hanya tombol **`Publish` / `Publish Ticket`** yang tersedia.
  * Saat status **beranjak dari Draft** (`open`, `assigned`, `in_progress`, `dept_mgr_approval`, `kadept_approval`, `bpo_approval`, `it_mgr_review`, `it_kadept_approval`), pengguna role Employee/Requester dapat melakukan **`Reject`** (Reject CR / Reject Ticket) untuk mengembalikan pengajuan kembali ke status **Draft** beserta memasukkan catatan alasannya.

---

### 13. Audit Logika Tiket, Auto-Routing, & Perhitungan SLA Response
* **Perbaikan Referensi Form View Tiket (`action_submit_create`)**:
  * Mengoreksi xml id `it_helpdesk.view_helpdesk_ticket_form` menjadi `it_helpdesk_v2.view_helpdesk_ticket_form` pada pemanggilan aksi buka tiket setelah submit.
* **Penyempurnaan `action_publish()`**:
  * Otomatis mereset catatan revisi/penolakan (`rejection_reason = False`) saat tiket diajukan ulang dari status `draft`.
  * Status tiket berpindah murni ke `Open`, dan kolom `engineer_id` dipastikan tetap kosong (*unassigned*). Penugasan Engineer kini sepenuhnya hanya berjalan saat tombol **"Assign / Eskalasi ke Engineer"** diklik oleh IT Admin.
* **Perbaikan Auto-Routing Engineer (`_auto_route_engineer`)**:
  * Menggunakan `subcat_id`, `cat_id`, dan `srv_id` (fallback ke record `self`) sehingga pencocokan aturan routing berjalan presisi saat penugasan manual via tombol *Assign*.
  * Menghapus fallback penugasan otomatis ke pembuat tiket (`engineer_id = self.env.uid`). Jika tidak ada aturan routing yang cocok, tiket tetap berstatus `unassigned` (`False`), mencegah tiket langsung tertutup/dikerjakan sendiri oleh pelapor.
* **Presisi Perhitungan SLA First Response Date**:
  * Pada method `action_assign_engineer` dan `action_start_progress`, sistem otomatis mencatat `first_response_date = fields.Datetime.now()` jika belum terisi, memastikan durasi SLA Response Time terhitung secara akurat.
* **Logika Tombol Reject Tiket (`_compute_can_reject`)**:
  * Menambahkan dependensi `@api.depends('state')` dan menonaktifkan hak reject pada status terminal (`draft`, `done`, `closed`, `reject`).
* **Penyelarasan Tampilan & Status Badge**:
  * Memperbaiki banner peringatan unassigned tiket dari kondisi `state != 'new'` menjadi `state != 'open'` pada form view.
  * Menyelaraskan pewarnaan badge status (`assigned`, `in_progress`, dll.) di Form View dan Kanban My Ticket.

---

### 14. Matriks Lengkap Hak Akses Pengguna Login (Menu, Tombol, & Kontrol Edit)
Rekapitulasi hak akses peranan (Role Matrix) saat pengguna login:

#### A. Akses Menu Navigasi (Muncul vs Di-Hide)
| Menu Navigasi | 1. Employee (Requester) | 2. Manager Dept. | 3. IT Manager | 4. IT Admin |
| :--- | :---: | :---: | :---: | :---: |
| **IT Helpdesk (Root)** | **MUNCUL** | **MUNCUL** | **MUNCUL** | **MUNCUL** |
| ├── **Dashboard (KPI & Analitik)** | HIDE | HIDE | **MUNCUL** | **MUNCUL** |
| ├── **Ticket** | | | | |
| │   ├── **All Ticket** | HIDE | HIDE | **MUNCUL** | **MUNCUL** |
| │   ├── **My Ticket** | **MUNCUL** | **MUNCUL** | **MUNCUL** | **MUNCUL** |
| │   ├── **Assigned Tickets to Me** | HIDE | HIDE | **MUNCUL** | **MUNCUL** |
| │   ├── **Assigned CR to Me** | HIDE | HIDE | **MUNCUL** | **MUNCUL** |
| │   └── **Create Ticket** | **MUNCUL** | **MUNCUL** | **MUNCUL** | **MUNCUL** |
| ├── **Knowledge Base (Kamus Solusi)** | **MUNCUL** | **MUNCUL** | **MUNCUL** | **MUNCUL** |
| ├── **Change Request (CR)** | | | | |
| │   ├── **My Change Request** | **MUNCUL** | **MUNCUL** | **MUNCUL** | **MUNCUL** |
| │   ├── **Need My Approval** | HIDE | **MUNCUL** | **MUNCUL** | **MUNCUL** |
| │   ├── **Active Queue & Progress** | HIDE | **MUNCUL** | **MUNCUL** | **MUNCUL** |
| │   ├── **All Change Requests** | **MUNCUL** *(Data terfilter)* | **MUNCUL** | **MUNCUL** | **MUNCUL** |
| │   └── **CR History & Archives** | HIDE | HIDE | **MUNCUL** | **MUNCUL** |
| ├── **Reports (Laporan & Pivot)** | HIDE | HIDE | **MUNCUL** | **MUNCUL** |
| └── **Configuration (Master Data & Setup)** | HIDE | HIDE | HIDE | **MUNCUL** |

#### B. Kontrol Tombol Aksi & Field Keamanan
* **Tombol Edit Utama Header Form (`static/src/js/helpdesk_form_control.js`)**:
  * Untuk **Employee biasa**: Tombol Edit **OTOMATIS DI-HIDE** begitu tiket / CR melewati status `Draft`.
  * Untuk **Manager Dept, IT Manager, IT Admin**: Tombol Edit **TETAP MUNCUL**.
* **Penugasan & Reassign Tiket**:
  * Tombol *Assign / Eskalasi ke Engineer* dan wizard *Eskalasi / Reassign Engineer* dilindungi grup `group_helpdesk_manager` (**Hanya IT Admin**).
* **Pengerjaan Tiket**:
  * Tombol *Start Progress* dan *Mark as Done* hanya muncul untuk tim pengelola (Manager Dept, IT Manager, IT Admin).
* **Field `engineer_id`**:
  * Readonly bagi Employee; dapat dipilih dan diedit oleh Manager Dept, IT Manager, dan IT Admin.
* **Koreksi SLA Time (Resolved & Closed Date)**:
  * Field tanggal penyelesaian dan penutupan tiket dapat diedit manual (*backdate/koreksi*) oleh **IT Admin** (`is_admin = True`).
* **Privasi Data Record Rules**:
  * Pada Change Request, pengguna Employee hanya dapat melihat record miliknya sendiri atau jika ditunjuk sebagai approver/engineer.

---

### 15. Evolusi Struktur Role Pengguna & Keamanan Penugasan Tiket (Assigned Ticket to)
* **Evolusi Penamaan & Fungsi Role**:
  * **Versi Awal**: Terdiri dari 3 role standar helpdesk Odoo:
    1. `group_helpdesk_user` (**Employee / Requester**)
    2. `group_helpdesk_agent` (**Engineer**)
    3. `group_helpdesk_manager` (**Helpdesk Officer**)
  * **Versi Saat Ini**: Ditingkatkan menjadi 4 role korporat untuk mengakomodasi alur persetujuan berjenjang:
    1. `group_helpdesk_user` (**Employee**) — Diwarisi semua pengguna internal Odoo.
    2. `group_helpdesk_agent` (**Manager Dept.**) — Difokuskan untuk persetujuan (approval) Change Request level unit/departemen pemohon.
    3. `group_helpdesk_it_manager` (**IT Manager**) — Persetujuan Change Request level IT dan akses pelaporan analitik.
    4. `group_helpdesk_manager` (**IT Admin**) — Administrator penuh sistem helpdesk dan master konfigurasi.
* **Validasi Keamanan Fungsi "Assigned Ticket to"**:
  * **Pemilihan Fleksibel**: Kolom penugasan `engineer_id` berelasi langsung ke `res.users` dengan domain `[('share', '=', False)]`, sehingga seluruh personil internal tim IT dapat ditugaskan sebagai penanggung jawab tiket tanpa terikat batasan nama role.
  * **Wewenang Penugasan**: Hak menetapkan teknisi (*Assign Engineer* & *Reassign Wizard*) dipegang penuh secara aman oleh peran **IT Admin**.
  * **Menu "Assigned to Me"**: Filter membaca record dengan kriteria `[('engineer_id', '=', uid)]`, sehingga tiket yang ditugaskan otomatis tampil di dashboard teknisi terkait.
  * **Notifikasi Email**: Pemicu otomatis `_send_engineer_assignment_email()` tetap mengirim email notifikasi tugas baru dan mencatat aktivitas di Chatter.

---

### 16. Pemisahan (Decoupling) Auto-Routing dari Tombol Publish Tiket
* **Alur Baru Pemisahan Status `open` dan `assigned` (`models/helpdesk_ticket.py`)**:
  * Sebelumnya, saat tombol **"Publish Ticket"** (`action_publish`) ditekan atau tiket dibuat dengan `publish_ticket=True`, sistem langsung menjalankan `_auto_route_engineer()` sehingga tiket langsung berpindah ke `open` dan otomatis ter-assign ke Engineer.
  * **Perubahan**: Logika `_auto_route_engineer()` dicabut dari `action_publish()` dan method `create()`.
  * **Hasil**:
    1. Klik **"Publish Ticket"** hanya mengubah status tiket dari `draft` ke `open`, dan kolom `engineer_id` dipastikan tetap **kosong / Unassigned** (`engineer_id = False`).
    2. Tiket baru akan di-assign ke engineer yang sesuai jika dan hanya jika IT Admin mengklik tombol **"Assign / Eskalasi ke Engineer"** (`action_assign_engineer`), yang kemudian mengubah status tiket ke `assigned` dan menempatkan Engineer sesuai matriks kata kunci / kategori.
  * **Perbaikan Routing Existing Ticket**: Method `_auto_route_engineer()` disempurnakan untuk memeriksa nilai `self.subcategory_id`, `self.category_id`, dan `self.service_id` pada record saat penugasan dipicu pasca-publish.
  * **Unit Test Verifikasi (`tests/test_ticket.py`)**: Menambahkan pengujian `test_publish_keeps_unassigned_until_action_assign` yang membuktikan secara otomatis bahwa tiket setelah di-publish tetap unassigned hingga `action_assign_engineer()` dipanggil.

---

### 17. Restrukturisasi Tab Container: Penggantian Tab Description Menjadi Tab "Expected Result & Link"
* **Penyatuan Komponen Informasi Kendala (`views/helpdesk_ticket_views.xml` & `views/helpdesk_create_ticket_views.xml`)**:
  * Menggantikan tab lama **`Description`** dengan tab baru berlabel gabungan: **`Expected Result & Link`** (mengadopsi struktur penamaan pada report kendala Excel "Nilai Seharusnya dan Link").
  * **Struktur Isi Tab `Expected Result & Link`**:
    1. **Expected Result (`expected_result`)**: Area teks untuk mengisi nilai / kondisi yang seharusnya diharapkan (placeholder: *"Tuliskan nilai / kondisi yang seharusnya diharapkan..."*).
    2. **Link (`excel_link`)**: Input URL berspesifikasi `widget="url"` untuk menyertakan tautan dokumen atau modul kendala terkait (placeholder: *"https://... (tautan dokumen / modul kendala)"*).
    3. **Attachment (`attachment_ids`)**: Kontainer berkas upload pendukung berspesifikasi `widget="many2many_binary"`.
  * **Eliminasi Redundansi**:
    * Menghapus duplikasi field `expected_result` dan `excel_link` dari tab *Detail Kendala Proyek (Import)*.
    * Menghapus tab *Attachment* yang berdiri sendiri, sehingga lampiran terpusat langsung di dalam tab *Expected Result & Link*.
    * Desain diterapkan seragam pada form *Create Ticket* dan *Detail Ticket*.

---

### 18. Restrukturisasi Tree/List View Tiket (11 Kolom Laporan Kendala & Base UX Optimization)
* **Penyelarasan Kolom Header Tree View (`views/helpdesk_ticket_views.xml`)**:
  * Mengadaptasi susunan tabel laporan kendala proyek (format Excel) ke dalam list view utama Odoo (`view_helpdesk_ticket_list`), terdiri dari 11 kolom terurut rapi:
    1. **Ticket No.** (`name`): Teks tebal berwarna biru sebagai tautan langsung ke detail tiket.
    2. **Proyek** (`location_id`, `optional="show"`): Menampilkan nama Proyek / Lokasi pelapor.
    3. **Judul** (`title`): Menampilkan judul kendala yang dihadapi.
    4. **Nilai seharusnya** (`expected_result`, `optional="show"`): Nilai/kondisi yang diharapkan pelapor.
    5. **Link** (`excel_link`, `widget="url"`, `optional="show"`): Tautan langsung ke dokumen/sistem kendala.
    6. **Tanggal Input Laporan** (`created_date`, `optional="show"`): Tanggal dan waktu pelaporan tiket.
    7. **Tanggal TL Laporan (IT)** (`followup_date_it`, `optional="show"`): Tanggal tindak lanjut IT.
    8. **Engineer** (`engineer_id`, `widget="many2one_avatar_user"`): Foto avatar dan nama teknisi IT penanggung jawab.
    9. **Status** (`state`, `widget="badge"`): Badge indikator alur status kerja tiket (*Draft*, *Open*, *Progress*, *Done*, dll.).
    10. **Priority** (`priority`, `widget="badge"`): Badge indikator prioritas (*P1 - Critical* s/d *P4 - Low*).
    11. **SLA Status** (`sla_status_name`, `widget="badge"`): Badge indikator batas waktu SLA (*On Track*, *SLA Overdue*, dll.).
* **Penyediaan Kolom Cadangan (`optional="hide"`)**:
  * Kolom `service_id` (*Service*) dan `requester_id` (*Requester*) dipertahankan dengan atribut `optional="hide"`, sehingga pengguna dapat memunculkannya sewaktu-waktu melalui tombol titik tiga (`⋮`) di pojok kanan atas tabel tanpa memadati layar.
* **Auto-Sync Metadata Lokasi & PIC (`models/helpdesk_ticket.py`)**:
  * Menambahkan sinkronisasi otomatis antara `location_id` dan `location_name` pada method `create()` dan `@api.onchange('location_id')`.
  * Menambahkan sinkronisasi otomatis `requester_name` dari `requester_id` dan `engineer_name` dari `engineer_id` untuk menjamin konsistensi data riwayat impor Excel dan tiket baru.
* **Peningkatan Search View (`view_helpdesk_ticket_search`)**:
  * Menambahkan field pencarian cepat `location_id` (*Proyek*) dan `expected_result` (*Nilai Seharusnya*) ke dalam panel pencarian tiket.

---

### 19. Penegakan Input Mandatory (Wajib Diisi) Tiket & Change Request
* **IT Helpdesk Ticket**:
  * Menegakkan validasi ketat via Python `UserError` pada method `action_publish()` (`models/helpdesk_ticket.py`) serta atribut visual `attrs="{'required': [('state', '=', 'draft')]}"` pada form view (`helpdesk_create_ticket_views.xml` & `helpdesk_ticket_views.xml`):
    1. **Judul Kendala** (`title`)
    2. **Jenis Tiket** (`ticket_type`)
    3. **Layanan / Service** (`service_id`)
    4. **Kategori Kendala** (`category_id`)
    5. **Departemen / Lokasi Proyek** (`location_id`)
    6. **No. Handphone / WhatsApp** (`phone`)
    7. **5 Pertanyaan Prioritas (Dampak & Urgensi)** (`q1_answer_id` s/d `q5_answer_id`)
    8. **Nilai Seharusnya** (`expected_result`)
    9. **Link Dokumen / Modul Kendala** (`excel_link`)
  * **Fleksibilitas Lampiran**: Berkas lampiran / Attachment (`attachment_ids`) bersifat opsional (tidak wajib diisi).
* **Change Request (CR)**:
  * Menegakkan validasi `action_submit()` (`models/helpdesk_change_request.py`) serta atribut visual `required` di XML:
    1. **Request Identification / Judul CR** (`request_identification`)
    2. **CR Type** (`cr_type_id`)
    3. **Category** (`category_id`) & **Sub Category** (`subcategory_id`)
    4. **CR to Departement** (`target_department_id`)
    5. **Impact On** (`impact_on`)
    6. **Attachment File** (`attachment_ids`) — Pelapor wajib melampirkan berkas dokumen/file pendukung sebelum submit.
  * **Klarifikasi Input Engineer / IT Admin**:
    * Field **Analysis & Solution** (`analysis_and_solution`) dikhususkan sebagai isian dari sisi teknisi IT / Engineer. Field ini diatur readonly bagi pelapor biasa, dan dapat diedit oleh Engineer / Officer IT selama status aktif.

---

### 20. Revisi Form Change Request (Penyederhanaan & UX Upload)
* **Penghapusan Input "Module"**:
  * Menghapus input field `module` dari tampilan form Change Request (`views/helpdesk_change_request_views.xml`).
* **Penghapusan Tab "Propose Solution"**:
  * Menghapus tab/page `propose_solution` dari notebook form Change Request.
* **Deskripsi Petunjuk Upload Attachment**:
  * Pada tab `ATTACHMENT`, tepat di atas kontainer upload file, ditambahkan banner informasi:
    * `"Upload dokumen/file pendukung Change Request"` lengkap dengan styling info banner dan ikon `fa-info-circle`.

---

### 21. Optimalisasi Form & Data Knowledge Base (Pusat Solusi Mandiri)
* **Perbaikan Visibilitas Label Form (`views/helpdesk_knowledge_views.xml`)**:
  * Mengganti struktur custom HTML div yang memudarkan teks (`text-secondary` tak kasat mata) dengan standar semantic group dan `<label for="...">` dengan warna kontras tinggi (`text-dark` / `#30354A`).
  * Label **Judul Solusi / Artikel Panduan**, **Klasifikasi Layanan & Kategori**, **Quick Solution?**, **Deskripsi / Gejala Masalah**, dan **Attachment** kini terbaca jelas dan tajam.
* **Kelengkapan Hierarki Kategori & Auto-Sync (`models/helpdesk_knowledge.py`)**:
  * Menambahkan input **Service / Layanan** (`service_id`) dan **Kategori** (`category_id`) berdampingan dengan **Sub Kategori** (`subcategory_id`).
  * Menambahkan event `@api.onchange` berjenjang:
    * Memilih Service otomatis memfilter Kategori.
    * Memilih Kategori otomatis mengisi Service dan memfilter Sub Kategori.
    * Memilih Sub Kategori otomatis mengisi Kategori dan Service induknya.
  * Menambahkan perlindungan di method `create()` dan `write()` untuk memastikan artikel yang disimpan langsung dari form maupun tiket selalu tersinkronisasi `service_id` dan `category_id`-nya.
* **Penyempurnaan Area Editor Panduan & Lampiran**:
  * Menambahkan header section visual: *"Langkah-Langkah & Panduan Solusi (Tutorial)"* dengan ikon buku dan instruksi menempelkan gambar screenshot.
  * Menambahkan badge status *"Opsional"* dan instruksi upload file pada kontainer Attachment.
* **Penambahan Search View Lengkap**:
  * Menambahkan `view_helpdesk_knowledge_search` untuk memfasilitasi pencarian artikel berdasarkan kata kunci judul/isi masalah, filter *Quick Solution*, *Artikel Saya*, *Archived*, serta *Group By* per Layanan, Kategori, Sub Kategori, dan Penulis.
* **Automated Unit Testing (`tests/test_knowledge.py`)**:
  * Menambahkan unit test case untuk memverifikasi auto-sync hierarki dan hak akses penghapusan artikel KB (hanya Manager yang berhak).

---

## 📂 Daftar File Modul `it_helpdesk_v2`

| Path File | Keterangan Status |
| :--- | :--- |
| `it_helpdesk_v2/__manifest__.py` | **Modified** — Registrasi file view, wizard, & model baru |
| `it_helpdesk_v2/hooks.py` | **Modified** — `post_init_hook` & auto-sync 744 user to employee |
| `it_helpdesk_v2/models/__init__.py` | **Modified** — Import `helpdesk_cr_type` & `hr_employee` |
| `it_helpdesk_v2/models/helpdesk_change_request.py` | **Modified** — Notifikasi email Manager IT, reset rejection_reason saat submit, perlindungan reject di status done/closed, queue number aman saat reopen, dan penanganan departemen IT |
| `it_helpdesk_v2/models/helpdesk_ticket.py` | **Modified** — Direct email sending (`force_send=True`), init auto-sql update, & write restriction |
| `it_helpdesk_v2/models/helpdesk_cr_type.py` | **New File** — Model master data CR Type |
| `it_helpdesk_v2/models/helpdesk_keyword.py` | **Modified** — Dynamic category & subcategory onchange filters |
| `it_helpdesk_v2/models/hr_employee.py` | **New File** — Fields `kadept_id` & `indirect_manager_id` & auto-link user |
| `it_helpdesk_v2/models/res_users.py` | **Modified** — Real-time auto-sync `res.users` ke `hr.employee` |
| `it_helpdesk_v2/security/helpdesk_security.xml` | **Modified** — Grouping role & Record Rules Change Request |
| `it_helpdesk_v2/security/ir.model.access.csv` | **Modified** — ACL master data CR Type & CR Reject Wizard |
| `it_helpdesk_v2/data/mail_template_data.xml` | **Modified** — Update `email_from` sender ke `system.itd@hkinfrastruktur.com` |
| `it_helpdesk_v2/data/helpdesk_email_template_data.xml` | **Modified** — Update `email_from` sender ke `system.itd@hkinfrastruktur.com` |
| `it_helpdesk_v2/data/helpdesk_change_request_email_template_data.xml` | **Modified** — Perbaikan ekspresi `${object.category_id.name}` & update email sender |
| `it_helpdesk_v2/tests/test_helpdesk_change_request_email.py` | **Modified** — Automated test suite 5-level approval & wizard rejection verification |
| `it_helpdesk_v2/views/helpdesk_change_request_views.xml` | **Modified** — Form view readonly state attrs, rejection banner, alur 5-level approval, statusbar dinamis (hide Approval Kadept BPO saat target IT), tombol reject disembunyikan di status done, & penambahan search view lengkap |
| `it_helpdesk_v2/views/helpdesk_ticket_views.xml` | **Modified** — Form view readonly state attrs & rejection wizard integration |
| `it_helpdesk_v2/views/helpdesk_create_ticket_views.xml` | **Modified** — Form view readonly state attrs for create ticket form |
| `it_helpdesk_v2/views/helpdesk_cr_type_views.xml` | **New File** — Views master data CR Type |
| `it_helpdesk_v2/views/helpdesk_keyword_views.xml` | **Modified** — Dynamic domains Kategori & Sub Kategori |
| `it_helpdesk_v2/views/helpdesk_menus.xml` | **Modified** — Penyesuaian parent menu 882 & hak akses menu |
| `it_helpdesk_v2/views/hr_employee_views.xml` | **New File** — Form view Employee (urutan Head of Placement ➔ Indirect ➔ Direct Manager) |
| `it_helpdesk_v2/wizard/helpdesk_cr_reject_wizard.py` | **New File** — Transient model wizard penolakan Change Request |
| `it_helpdesk_v2/wizard/helpdesk_cr_reject_wizard_views.xml` | **New File** — Form view pop-up dialog Reject CR |
| `it_helpdesk_v2/models/helpdesk_knowledge.py` | **Modified** — Auto-sync hierarki Service/Category/Subcategory, onchanges, & problem sync |
| `it_helpdesk_v2/views/helpdesk_knowledge_views.xml` | **Modified** — Redesign layout form, high-contrast labels, service/category inputs, & search view |
| `it_helpdesk_v2/tests/test_knowledge.py` | **New File** — Automated unit tests hierarki, onchange, & hak akses unlink KB |


