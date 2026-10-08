# Rekap Perubahan Modul `it_helpdesk_v2`

**Tanggal Rekap Terbaru:** 06 Oktober 2026  
**Referensi Commit Terakhir (GitHub):** `8c6101f Feat: Add dynamic category and subcategory filtering in Keyword Routing Rules`  
**Repository GitHub:** `https://github.com/miqiqbal/addons_iian.git` (Branch: `main`)  
**Status:** All Local Changes Committed & Pushed to Remote GitHub

---

## 📌 Ringkasan Utama Perubahan

Pembaruan pada modul **`it_helpdesk_v2`** berfokus pada **8 area utama**:

1. **Master Data Fitur Baru: CR Type (`helpdesk.cr.type`)**.
2. **Perombakan Workflow Approval Change Request Multi-Tier (5-Level Flow)**.
3. **Integrasi & Auto-Sync Otomatis User (`res.users`) ➔ Employee (`hr.employee`)**.
4. **Ekstensi Struktur Organisasi HR & Penataan Form Employee**.
5. **Dynamic Filtering pada Keyword Routing Rules (`helpdesk.keyword`)**.
6. **Penyesuaian Hak Akses & Peran Pengguna (Group & Security Access)**.
7. **Automated Unit Testing Suite**.
8. **Pembaruan Pengirim Email Notifikasi (`system.itd@hkinfrastruktur.com`)**.

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

## 📂 Daftar File Modul `it_helpdesk_v2`

| Path File | Keterangan Status |
| :--- | :--- |
| `it_helpdesk_v2/__manifest__.py` | **Modified** — Registrasi file view, wizard, & model baru |
| `it_helpdesk_v2/hooks.py` | **Modified** — `post_init_hook` & auto-sync 744 user to employee |
| `it_helpdesk_v2/models/__init__.py` | **Modified** — Import `helpdesk_cr_type` & `hr_employee` |
| `it_helpdesk_v2/models/helpdesk_change_request.py` | **Modified** — Domain target dept, BPO job matching, dialog reject, & write restriction |
| `it_helpdesk_v2/models/helpdesk_ticket.py` | **Modified** — Direct email sending (`force_send=True`), init auto-sql update, & write restriction |
| `it_helpdesk_v2/models/helpdesk_cr_type.py` | **New File** — Model master data CR Type |
| `it_helpdesk_v2/models/helpdesk_keyword.py` | **Modified** — Dynamic category & subcategory onchange filters |
| `it_helpdesk_v2/models/hr_employee.py` | **New File** — Fields `kadept_id` & `indirect_manager_id` & auto-link user |
| `it_helpdesk_v2/models/res_users.py` | **Modified** — Real-time auto-sync `res.users` ke `hr.employee` |
| `it_helpdesk_v2/security/helpdesk_security.xml` | **Modified** — Grouping role & Record Rules Change Request |
| `it_helpdesk_v2/security/ir.model.access.csv` | **Modified** — ACL master data CR Type & CR Reject Wizard |
| `it_helpdesk_v2/data/mail_template_data.xml` | **Modified** — Update `email_from` sender ke `system.itd@hkinfrastruktur.com` |
| `it_helpdesk_v2/data/helpdesk_email_template_data.xml` | **Modified** — Update `email_from` sender ke `system.itd@hkinfrastruktur.com` |
| `it_helpdesk_v2/data/helpdesk_change_request_email_template_data.xml` | **Modified** — Update `email_from` sender ke `system.itd@hkinfrastruktur.com` |
| `it_helpdesk_v2/tests/test_helpdesk_change_request_email.py` | **Modified** — Automated test suite 5-level approval |
| `it_helpdesk_v2/views/helpdesk_change_request_views.xml` | **Modified** — Form view readonly state attrs, rejection banner, & alur 5-level approval |
| `it_helpdesk_v2/views/helpdesk_ticket_views.xml` | **Modified** — Form view readonly state attrs & rejection wizard integration |
| `it_helpdesk_v2/views/helpdesk_create_ticket_views.xml` | **Modified** — Form view readonly state attrs for create ticket form |
| `it_helpdesk_v2/views/helpdesk_cr_type_views.xml` | **New File** — Views master data CR Type |
| `it_helpdesk_v2/views/helpdesk_keyword_views.xml` | **Modified** — Dynamic domains Kategori & Sub Kategori |
| `it_helpdesk_v2/views/helpdesk_menus.xml` | **Modified** — Penyesuaian parent menu 882 & hak akses menu |
| `it_helpdesk_v2/views/hr_employee_views.xml` | **New File** — Form view Employee (urutan Head of Placement ➔ Indirect ➔ Direct Manager) |
| `it_helpdesk_v2/wizard/helpdesk_cr_reject_wizard.py` | **New File** — Transient model wizard penolakan Change Request |
| `it_helpdesk_v2/wizard/helpdesk_cr_reject_wizard_views.xml` | **New File** — Form view pop-up dialog Reject CR |


