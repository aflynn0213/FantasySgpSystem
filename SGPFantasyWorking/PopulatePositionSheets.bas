Attribute VB_Name = "Module2"
Sub FLYNN()
    Dim wb As Workbook
    Dim wsSource As Worksheet
    Dim wsSGP As Worksheet
    Dim wsDestination As Worksheet
    Dim lastRow As Long, i As Long, destRow As Long
    Dim lookupValue As Variant
    Dim lookupResult As Variant
    Dim colOffset As Long
    Dim headerRange As Range
    Dim destinationSheetNames As Variant
    Dim destinationKeywords As Variant
    Dim keywordIndex As Long
    
    ' Specify the workbook
    Set wb = Workbooks.Open("C:\FantBaseball\LeagueStatsSGPInvest.xlsx")
    
    ' Verify source worksheet existence
    On Error Resume Next
    Set wsSource = wb.Sheets("AUC Calc HIT POOL 24")
    On Error GoTo 0
    If wsSource Is Nothing Then
        MsgBox "Source worksheet not found!", vbExclamation
        Exit Sub
    End If
    
    ' Verify SGP worksheet existence
    On Error Resume Next
    Set wsSGP = wb.Sheets("SGP HIT '24")
    On Error GoTo 0
    If wsSGP Is Nothing Then
        MsgBox "SGP worksheet not found!", vbExclamation
        Exit Sub
    End If
    
    ' Define destination sheet names and keywords
    destinationSheetNames = Array("C", "1B", "2B", "3B", "SS", "OF", "DH")
    destinationKeywords = Array("C", "1B", "2B", "3B", "SS", "OF", "DH")
    
    ' Loop through each destination sheet
    For keywordIndex = LBound(destinationKeywords) To UBound(destinationKeywords)
        ' Set destination worksheet
        Set wsDestination = wb.Sheets(destinationSheetNames(keywordIndex))
        
        ' Write header row to destination sheet (only once)
        If destRow = 0 Then
            Set headerRange = wsDestination.Range("A1:M1")
            headerRange.Value = Array("ID", "NAME", "TEAM", "POS", "R/SGP", "RBI/SGP", "HR/SGP", "SB/SGP", "OBP/SGP", "SLUG/SGP", "SUM", "RL", "VAR")
        End If
        
        ' Find the last row in the source sheet
        lastRow = wsSource.Cells(wsSource.Rows.Count, "A").End(xlUp).Row
        
        ' Set destination row to next row after header
        If destRow = 0 Then
            destRow = 2
        End If
        
        ' Loop through each row in the source sheet
        For i = 2 To lastRow ' Assuming data starts from row 2 and the criteria is in column A
            ' Check if the cell in column D contains the desired keyword
            If InStr(1, wsSource.Cells(i, "D").Value, destinationKeywords(keywordIndex), vbTextCompare) > 0 Then
                ' Get the lookup value from the source sheet
                lookupValue = wsSource.Cells(i, "A").Value ' Assuming the lookup value is in column A
                
                ' Loop through columns E to M
                For colOffset = 0 To 8 ' Corresponds to columns E to M
                    ' Perform VLOOKUP to get additional data from SGP sheet
                    lookupResult = Application.VLookup(lookupValue, wsSGP.Range("B:N"), colOffset + 5, False)
                    
                    ' Check if VLOOKUP found a match
                    If Not IsError(lookupResult) Then
                        ' Write VLOOKUP result to destination sheet
                        wsDestination.Cells(destRow, "E").Offset(0, colOffset).Value = lookupResult
                    End If
                Next colOffset
                
                ' Copy columns A through D from source sheet to destination sheet
                wsSource.Range("A" & i & ":D" & i).Copy wsDestination.Range("A" & destRow)
                destRow = destRow + 1 ' Increment destination row
            End If
        Next i
        
        ' Reset destination row for the next destination sheet
        destRow = 0
    Next keywordIndex
End Sub

