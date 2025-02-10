# rcv
Ranked Choice Voting utilities and experiments, mostly associated with [CalRCV](https://calrcv.org/).

## How to set up this code

1. Open a Terminal window and download out this repository:
   ```sh
   git clone https://github.com/egnor/rcv
   ```

   You should see something like this
   ```
   $ git clone https://github.com/egnor/rcv
   Cloning into 'rcv'...
   remote: Enumerating objects: 163, done.
   remote: Counting objects: 100% (163/163), done.
   remote: Compressing objects: 100% (103/103), done.
   remote: Total 163 (delta 73), reused 123 (delta 39), pack-reused 0 (from 0)
   Receiving objects: 100% (163/163), 46.88 KiB | 2.13 MiB/s, done.
   Resolving deltas: 100% (73/73), done.
   ```
  
2. Also, install ["mise"](https://mise.jdx.dev/) on your computer [following these instructions](https://mise.jdx.dev/getting-started.html).

   (Mise is a tool manager, so you only have to install this one thing and it can set up everything else.)
  
3. Then, `cd` to the repository and use `mise` to set everything else up:
   ```sh
   cd rcv
   mise trust
   mise run setup
   ```

   You should see something like this
   ```
   $ cd rcv
   mise ERROR error parsing config file: ~/rcv/mise.toml
   mise ERROR Config file ~/rcv/mise.toml is not trusted.
   Trust it with `mise trust`.

   $ mise trust
   mise trusted /home/egnor/rcv/mise.toml
   mise creating venv with stdlib at: ~/rcv/venv.tmp                               
   mise python@3.10.16 node@22.12.0
   mise +VIRTUAL_ENV

   $ mise run setup
   [setup] $ mise install 
   mise all runtimes are installed
   [setup] $ mise x -- python3 -m pip install -q --disable-pip-version-check -e .[dev]
   ```

If you got weird errors, let me (egnor) know. Otherwise you should be good to go...

## Importing contributions from NationBuilder into EveryAction

The way this works: We download a record of all transactions so far from both
EveryAction and NationBuilder. Then we run this code which converts the NB transactions
to EA format, and removes any transactions already in EA, producing a file which we
bulk upload to EA.

1. Make sure this code is ready to run (instructions above).

2. Log in to [the NationBuilder admin panel for CalRCV](https://calrcv.nationbuilder.com/admin/).

3. Select [the "Finances" entry](https://calrcv.nationbuilder.com/admin/financial_transactions) in the sidebar.

   ![image](https://github.com/user-attachments/assets/cdf9faa9-57ce-437a-b422-ab89fdde43f9)

4. Select ["Export" from the "Actions" menu](https://calrcv.nationbuilder.com/admin/financial_transaction_exports) (upper right)

   ![image](https://github.com/user-attachments/assets/27db14d3-5445-4890-8445-c163340e85f0)

5. You'll see a list of export jobs, with a new one "Export pending..." at the top

   ![image](https://github.com/user-attachments/assets/5d535502-4c16-4c95-8c21-b7de21bdf34f)

6. Reload the export page until instead of "pending..." it shows a file to download

   ![image](https://github.com/user-attachments/assets/5f8910fc-e297-46c7-9475-708f9bdfd479)

7. Click to download the file and **save it to the `rcv` directory** (or move it there after download).

8. Now log into [the EveryAction dashboard](https://app.everyaction.com/)

9. Expand "Reporting" in the sidebar and [click on "Report Manager"](https://app.everyaction.com/ReportManager.aspx)

   ![image](https://github.com/user-attachments/assets/4dcc104a-a24c-471a-9eea-447bae9118aa)

10. Click on [the "NB import exclusion" report](https://app.everyaction.com/ReportViewer.aspx?ReportId=EID1B&TemplateID=EID28B71Q)
    (the custom report that exists for this purpose)

    ![image](https://github.com/user-attachments/assets/55f178a9-f55d-48ea-b594-c6187899af75)

11. Select "Text (.txt)" from the "Export As..." menu near the upper right

    ![image](https://github.com/user-attachments/assets/b5ea54f3-9b77-445a-85b2-dc566dbbc593)

12. You should get a message about "Export in Progress"

    ![image](https://github.com/user-attachments/assets/5a5de4eb-57f1-48ad-8af4-32eeb0be9568)

14. Once it's done it will show up in "Notifications" (bell icon at top of page)

    ![image](https://github.com/user-attachments/assets/c2dd2e1d-34ad-436d-ba2f-a4570d62fd0e)

15. Click to download the file and **save it to the `rcv` directory** (or move in there after download).

    In that directory, you should have two new data files (it's OK if older files are also present):
    - `nationbuilder-financialtransactions-export-NNN-YYYY-MM-DD.csv` (from NationBuilder)
    - `ContributionReport-NNNNNNNNNNNNNNNN.zip` (from EveryAction)
   
16. Now, in a Terminal window, enter the `rcv` directory and run the converter:
    ```sh
    cd rcv  # if you weren't already there
    nb_to_ea_financial
    ```

    You should see something like this
    ```
    $ nb_to_ea_financial
    ⬅️ ContributionReport-6195899609.txt ⬅️ ContributionReport-6195899609.zip
    ✅ 3404 rows: 3187 excludable transactions

    ⬅️ nationbuilder-financialtransactions-export-530-2025-02-10.csv
    ▶️ everyaction-financialtransactions-530-2025-02-10.txt
    ✅ 2066 rows - 2061 excluded = 5 written
    ```

    There should now be an `everyaction-financialtransactions-NNN-YYYY-MM-DD.txt` file.
    This is what we'll be uploading to EA.

17. Back on the EveryAction side, search for
    [the "Upload New File" page](https://app.everyaction.com/UploadDataSelectType.aspx#/)

    ![image](https://github.com/user-attachments/assets/e7b6386a-67a1-4c21-ba90-15d0b449bd7f)

    (In the older EveryAction interface, this is called the "Bulk Upload Wizard")

18. Select "Load new and/or make changes to existing contacts", then click "Next"
    
    ![image](https://github.com/user-attachments/assets/3678f2ce-894d-4e74-983b-1161edeace51)

19. Scroll down and select a "Saved" Mapping Template. The page will reload...

    ![image](https://github.com/user-attachments/assets/1760310a-209f-40bb-a61d-8bbf13cedc7d)

20. Select "NationBuilder financial transactions via egnor script"

    ![image](https://github.com/user-attachments/assets/a1d499e6-aceb-45a8-af8a-cd5e33f111b6)

21. Click "Select A File" and upload the `everyaction-financialtransactions-...` file:

    ![image](https://github.com/user-attachments/assets/5c95db7e-5b83-4151-bdaf-dd0321907500)

22. Click "Upload"

    ![image](https://github.com/user-attachments/assets/84df7a3f-be26-47f5-8a81-9f39ecfe07c9)

23. You should see a page that looks like this. The "Some columns that are mapped have no values"
    warning is normal.

    ![image](https://github.com/user-attachments/assets/5a6c63f1-95b7-4cad-baf5-12687535b7d9)

    At the bottom of the page you'll see a handful of sample records. Check that they look OK.

24. Finally, click "Finish" in the upper right of that page, and confirm the upload.

    ![image](https://github.com/user-attachments/assets/0411794a-50ff-4ad5-a40d-3111c961686c)

25. You should now see [a list of Bulk Upload Batches](https://app.everyaction.com/BulkUploadBatchesList.aspx#/),
    with new ones at the top (the job splits into several "batches" due to internal EA processing).
    **You're not done yet!** Click "Refresh Results"...

    ![image](https://github.com/user-attachments/assets/e624a13f-3b63-473e-833d-bb8bd077206a)

    ...until an option shows up to "Approve" the new upload:

    ![image](https://github.com/user-attachments/assets/ffa18399-8a6f-4779-9368-ece61dd916a3)

27. Click "Approve". Verify that ALL records are "ID Match" (by NationBuilder ID), and click "Next"

    ![image](https://github.com/user-attachments/assets/d1527318-426f-4a40-928f-a1c679d464f3)

28. Then click "Finish"

    ![image](https://github.com/user-attachments/assets/106b7623-68f3-4567-bf0d-15a1de67ff63)

29. *Now* you're basically done. If you're so inclined, you can click "Refresh Results" until
    the new batches show as "100% Processed":

    ![image](https://github.com/user-attachments/assets/91207ffd-3189-4703-88bb-e2a337ed074c)

Whew, that's it! 🎉
