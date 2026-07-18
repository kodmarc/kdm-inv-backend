import io
import datetime
from django.http import HttpResponse
from xhtml2pdf import pisa
from rest_framework import viewsets, mixins, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny  
from django.db import transaction
from .models import (
    OrderBooker, Salesman, Party, AccountOpening, 
    SalesInvoice, PurchaseInvoice, JournalEntry, JournalItem, 
    PurchaseReturn, DamageReturn,
    SalesReturn  # ✅ No DamageReceiving
)
from .serializers import (
    OrderBookerSerializer,
    SalesmanSerializer,
    PartySerializer,
    AccountOpeningSerializer,
    SalesInvoiceSerializer,
    PurchaseInvoiceSerializer,
    JournalItemSerializer,
    PurchaseReturnSerializer,
    DamageReturnSerializer,
    SalesReturnSerializer  
)


# ============== PDF RENDER FUNCTIONS ==============

def _render_sales_invoice_pdf(invoice, request, pdf_type):
    booker_name = invoice.order_booker.name if invoice.order_booker else '—'
    salesman_name = invoice.salesman.name if invoice.salesman else '—'
    
    title = 'Sales Invoice'
    if pdf_type == 'booker':
        title = 'Booker Copy'
    elif pdf_type == 's_tax':
        title = 'Sales Tax Invoice'

    rows_html = []
    for idx, line in enumerate(invoice.line_items.all()):
        item_name = line.item.name if line.item else '—'
        item_code = line.item.code if line.item else '—'
        
        row = f"""
        <tr class="{'even' if idx % 2 == 1 else 'odd'}">
            <td style="text-align: center;">{idx + 1}</td>
            <td>{item_name} ({item_code})</td>
            <td style="text-align: right;">{float(line.carton):.2f}</td>
            <td style="text-align: right;">{float(line.pcs):.2f}</td>
            <td style="text-align: right;">Rs. {float(line.rate):.2f}</td>
            <td style="text-align: right;">Rs. {float(line.amount):.2f}</td>
        """
        
        if pdf_type == 's_tax':
            row += f"""
            <td style="text-align: right;">Rs. {float(line.s_tax_amount):.2f}</td>
            <td style="text-align: right;">Rs. {float(line.f_tax_amount):.2f}</td>
            <td style="text-align: right;">Rs. {float(line.gross_amount):.2f}</td>
            """
            
        row += f"""
            <td style="text-align: right;">{float(line.to_rate):.2f}%</td>
            <td style="text-align: right;">Rs. {float(line.to_amount):.2f}</td>
            <td style="text-align: right; font-weight: bold;">Rs. {float(line.net_amount):.2f}</td>
        </tr>
        """
        rows_html.append(row)

    rows_html_str = "".join(rows_html)
    
    subtotal = sum(line.net_amount for line in invoice.line_items.all())
    total_s_tax = sum(line.s_tax_amount for line in invoice.line_items.all())
    total_f_tax = sum(line.f_tax_amount for line in invoice.line_items.all())
    
    branch_slug = invoice.branch.slug if invoice.branch else '—'
    company_name = invoice.company.name if invoice.company else '—'
    
    s_tax_summary_rows = ""
    if pdf_type == 's_tax':
        s_tax_summary_rows = f"""
        <tr>
          <td style="border: none; padding: 4px 0; color: #6b7280; font-weight: 500;">Total Sales Tax:</td>
          <td style="border: none; padding: 4px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(total_s_tax):.2f}</td>
        </tr>
        <tr>
          <td style="border: none; padding: 4px 0; color: #6b7280; font-weight: 500;">Total Further Tax:</td>
          <td style="border: none; padding: 4px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(total_f_tax):.2f}</td>
        </tr>
        """

    generated_time = datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p')
    status_color = "#16a34a" if invoice.status == 'paid' else "#dc2626"
    
    remarks_row = ""
    if invoice.remarks:
        remarks_row = f"""
        <tr>
          <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Remarks:</td>
          <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{invoice.remarks}</td>
        </tr>
        """

    company_ntn_row = f"<div>NTN: {invoice.ntn}</div>" if invoice.ntn else ""
    company_gst_row = f"<div>GST No: {invoice.gst_no}</div>" if invoice.gst_no else ""

    html = f"""
    <html>
      <head>
        <title>{title} - {invoice.sale_code}</title>
        <style>
          body {{ font-family: 'Helvetica', 'Arial', sans-serif; color: #1f2937; padding: 10px; line-height: 1.4; background: #fff; font-size: 10px; }}
          .items-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px; }}
          .items-table th {{ background-color: #1e3a8a; color: white; padding: 8px 10px; text-align: left; font-weight: bold; border: 1px solid #1e3a8a; font-size: 9px; }}
          .items-table td {{ border: 1px solid #e5e7eb; padding: 8px 10px; color: #374151; font-size: 9px; }}
          .items-table tr.even td {{ background-color: #f9fafb; }}
        </style>
      </head>
      <body>
        <table style="width: 100%; border-collapse: collapse; border-bottom: 3px solid #2563eb; margin-bottom: 20px; padding-bottom: 10px;">
          <tr>
            <td style="width: 50%; vertical-align: top; border: none; padding: 0;">
              <div style="font-size: 24px; font-weight: 800; color: #2563eb; text-transform: uppercase;">{title}</div>
              <div style="font-size: 14px; font-weight: 700; margin-top: 6px; color: #1e3a8a;">Code: {invoice.sale_code}</div>
              <div style="font-size: 11px; color: #6b7280; margin-top: 2px;">Date: {invoice.date}</div>
            </td>
            <td style="width: 50%; text-align: right; vertical-align: top; border: none; padding: 0;">
              <div style="font-weight: 800; font-size: 18px; color: #1e3a8a;">{company_name}</div>
              <div style="font-size: 12px; color: #4b5563;">Branch ID: {branch_slug}</div>
              {company_ntn_row}
              {company_gst_row}
            </td>
          </tr>
        </table>

        <table style="width: 100%; border: none; border-collapse: collapse; margin-bottom: 20px;">
          <tr>
            <td style="width: 48%; vertical-align: top; border: none; padding: 0; padding-right: 10px;">
              <table style="width: 100%; border: 1px solid #e5e7eb; background-color: #f9fafb; padding: 12px; font-size: 11px;">
                <tr>
                  <td style="border: none; padding: 0 0 8px 0; font-weight: bold; font-size: 12px; border-bottom: 1px solid #e5e7eb; color: #1f2937; text-transform: uppercase;">Customer / Party Details</td>
                </tr>
                <tr>
                  <td style="border: none; padding: 6px 0 0 0;">
                    <table style="width: 100%; border: none; font-size: 11px;">
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500; width: 45%;">Name:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right; width: 55%;">{invoice.party.name}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Payment Status:</td>
                        <td style="border: none; padding: 2px 0; font-weight: 600; text-align: right; color: {status_color}">{invoice.status.upper()}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Outstanding Balance:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(invoice.balance_amount):.2f}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Credit Limit:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(invoice.credit_limit):.2f}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Credit Days:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{invoice.credit_days} Days</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
            <td style="width: 48%; vertical-align: top; border: none; padding: 0; padding-left: 10px;">
              <table style="width: 100%; border: 1px solid #e5e7eb; background-color: #f9fafb; padding: 12px; font-size: 11px;">
                <tr>
                  <td style="border: none; padding: 0 0 8px 0; font-weight: bold; font-size: 12px; border-bottom: 1px solid #e5e7eb; color: #1f2937; text-transform: uppercase;">Ledger & Personnel Details</td>
                </tr>
                <tr>
                  <td style="border: none; padding: 6px 0 0 0;">
                    <table style="width: 100%; border: none; font-size: 11px;">
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500; width: 45%;">Order Booker:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right; width: 55%;">{booker_name}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Salesman:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{salesman_name}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Ledger Account:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{invoice.account.name}</td>
                      </tr>
                      {remarks_row}
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>

        <table class="items-table">
          <thead>
            <tr>
              <th style="width: 5%; text-align: center;">S.No</th>
              <th style="width: 25%;">Item Name</th>
              <th style="width: 10%; text-align: right;">Carton</th>
              <th style="width: 10%; text-align: right;">Pcs</th>
              <th style="width: 10%; text-align: right;">Rate</th>
              <th style="width: 10%; text-align: right;">Amount</th>
              {"<th style='width: 10%; text-align: right;'>S. Tax</th><th style='width: 10%; text-align: right;'>F. Tax</th><th style='width: 10%; text-align: right;'>Gross</th>" if pdf_type == 's_tax' else ''}
              <th style="width: 8%; text-align: right;">T.O Rate</th>
              <th style="width: 10%; text-align: right;">T.O Amt</th>
              <th style="width: 12%; text-align: right;">Net Amount</th>
            </tr>
          </thead>
          <tbody>
            {rows_html_str}
          </tbody>
        </table>

        <table style="width: 100%; border: none; border-collapse: collapse; margin-top: 20px;">
          <tr>
            <td style="width: 50%; border: none;"></td>
            <td style="width: 50%; border: none; padding: 0;">
              <table style="width: 100%; border: 1px solid #e5e7eb; background-color: #f9fafb; padding: 12px; font-size: 11px;">
                <tr>
                  <td style="border: none; padding: 4px 0; color: #6b7280; font-weight: 500; width: 50%;">Subtotal:</td>
                  <td style="border: none; padding: 4px 0; color: #1f2937; font-weight: 600; text-align: right; width: 50%;">Rs. {float(subtotal):.2f}</td>
                </tr>
                {s_tax_summary_rows}
                <tr>
                  <td style="border: none; padding: 4px 0; color: #6b7280; font-weight: 500;">Invoice Discount:</td>
                  <td style="border: none; padding: 4px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(invoice.discount):.2f}</td>
                </tr>
                <tr>
                  <td style="border: none; border-top: 2px dashed #2563eb; padding: 8px 0 0 0; font-weight: bold; color: #2563eb; font-size: 13px;">Grand Total:</td>
                  <td style="border: none; border-top: 2px dashed #2563eb; padding: 8px 0 0 0; font-weight: bold; color: #2563eb; font-size: 13px; text-align: right;">Rs. {float(invoice.net_amount):.2f}</td>
                </tr>
              </table>
            </td>
          </tr>
        </table>

        <div style="text-align: center; margin-top: 50px; font-size: 9px; color: #9ca3af; border-top: 1px solid #e5e7eb; padding-top: 15px;">
          Generated on {generated_time} | KDM POS System | Page 1 of 1
        </div>
      </body>
    </html>
    """
    return html


def _render_purchase_invoice_pdf(invoice, request):
    rows_html = []
    for idx, line in enumerate(invoice.line_items.all()):
        item_name = line.item.name if line.item else '—'
        item_code = line.item.code if line.item else '—'
        
        row = f"""
        <tr class="{'even' if idx % 2 == 1 else 'odd'}">
            <td style="text-align: center;">{idx + 1}</td>
            <td>{item_name} ({item_code})</td>
            <td style="text-align: right;">{float(line.carton):.2f}</td>
            <td style="text-align: right;">{float(line.pcs):.2f}</td>
            <td style="text-align: right;">Rs. {float(line.rate):.2f}</td>
            <td style="text-align: right;">Rs. {float(line.amount):.2f}</td>
            <td style="text-align: right;">Rs. {float(line.discount_amount):.2f}</td>
            <td style="text-align: right;">{float(line.to_rate):.2f}%</td>
            <td style="text-align: right;">Rs. {float(line.to_amount):.2f}</td>
            <td style="text-align: right;">{float(line.s_tax_rate):.2f}%</td>
            <td style="text-align: right;">Rs. {float(line.s_tax_amount):.2f}</td>
            <td style="text-align: right; font-weight: bold;">Rs. {float(line.net_amount):.2f}</td>
        </tr>
        """
        rows_html.append(row)

    rows_html_str = "".join(rows_html)
    
    subtotal = sum(line.net_amount for line in invoice.line_items.all())
    
    branch_slug = invoice.branch.slug if invoice.branch else '—'
    company_name = invoice.company.name if invoice.company else '—'
    
    generated_time = datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p')
    status_color = "#16a34a" if invoice.status == 'paid' else "#dc2626"
    
    remarks_row = ""
    if invoice.remarks:
        remarks_row = f"""
        <tr>
          <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Remarks:</td>
          <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{invoice.remarks}</td>
        </tr>
        """

    supplier_ntn_row = f"""
    <tr>
      <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">NTN:</td>
      <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{invoice.ntn}</td>
    </tr>
    """ if invoice.ntn else ""

    supplier_gst_row = f"""
    <tr>
      <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">GST No:</td>
      <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{invoice.gst_no}</td>
    </tr>
    """ if invoice.gst_no else ""

    html = f"""
    <html>
      <head>
        <title>Purchase Invoice - {invoice.purchase_code}</title>
        <style>
          body {{ font-family: 'Helvetica', 'Arial', sans-serif; color: #1f2937; padding: 10px; line-height: 1.4; background: #fff; font-size: 10px; }}
          .items-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px; }}
          .items-table th {{ background-color: #1e3a8a; color: white; padding: 8px 10px; text-align: left; font-weight: bold; border: 1px solid #1e3a8a; font-size: 9px; }}
          .items-table td {{ border: 1px solid #e5e7eb; padding: 8px 10px; color: #374151; font-size: 9px; }}
          .items-table tr.even td {{ background-color: #f9fafb; }}
        </style>
      </head>
      <body>
        <table style="width: 100%; border-collapse: collapse; border-bottom: 3px solid #2563eb; margin-bottom: 20px; padding-bottom: 10px;">
          <tr>
            <td style="width: 50%; vertical-align: top; border: none; padding: 0;">
              <div style="font-size: 24px; font-weight: 800; color: #2563eb; text-transform: uppercase;">Purchase Invoice</div>
              <div style="font-size: 14px; font-weight: 700; margin-top: 6px; color: #1e3a8a;">Code: {invoice.purchase_code}</div>
              <div style="font-size: 11px; color: #6b7280; margin-top: 2px;">Date: {invoice.date}</div>
            </td>
            <td style="width: 50%; text-align: right; vertical-align: top; border: none; padding: 0;">
              <div style="font-weight: 800; font-size: 18px; color: #1e3a8a;">{company_name}</div>
              <div style="font-size: 12px; color: #4b5563;">Branch ID: {branch_slug}</div>
            </td>
          </tr>
        </table>

        <table style="width: 100%; border: none; border-collapse: collapse; margin-bottom: 20px;">
          <tr>
            <td style="width: 48%; vertical-align: top; border: none; padding: 0; padding-right: 10px;">
              <table style="width: 100%; border: 1px solid #e5e7eb; background-color: #f9fafb; padding: 12px; font-size: 11px;">
                <tr>
                  <td style="border: none; padding: 0 0 8px 0; font-weight: bold; font-size: 12px; border-bottom: 1px solid #e5e7eb; color: #1f2937; text-transform: uppercase;">Supplier Details</td>
                </tr>
                <tr>
                  <td style="border: none; padding: 6px 0 0 0;">
                    <table style="width: 100%; border: none; font-size: 11px;">
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500; width: 45%;">Name:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right; width: 55%;">{invoice.supplier.name}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Payment Status:</td>
                        <td style="border: none; padding: 2px 0; font-weight: 600; text-align: right; color: {status_color}">{invoice.status.upper()}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Outstanding Balance:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(invoice.balance_amount):.2f}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Credit Limit:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(invoice.credit_limit):.2f}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Credit Days:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{invoice.credit_days} Days</td>
                      </tr>
                      {supplier_ntn_row}
                      {supplier_gst_row}
                    </table>
                  </td>
                </tr>
              </table>
            </td>
            <td style="width: 48%; vertical-align: top; border: none; padding: 0; padding-left: 10px;">
              <table style="width: 100%; border: 1px solid #e5e7eb; background-color: #f9fafb; padding: 12px; font-size: 11px;">
                <tr>
                  <td style="border: none; padding: 0 0 8px 0; font-weight: bold; font-size: 12px; border-bottom: 1px solid #e5e7eb; color: #1f2937; text-transform: uppercase;">Ledger Details</td>
                </tr>
                <tr>
                  <td style="border: none; padding: 6px 0 0 0;">
                    <table style="width: 100%; border: none; font-size: 11px;">
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500; width: 45%;">Ledger Account:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right; width: 55%;">{invoice.account.name}</td>
                      </tr>
                      {remarks_row}
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>

        <table class="items-table">
          <thead>
            <tr>
              <th style="width: 4%; text-align: center;">S.No</th>
              <th style="width: 24%;">Item Name</th>
              <th style="width: 8%; text-align: right;">Carton</th>
              <th style="width: 8%; text-align: right;">Pcs</th>
              <th style="width: 8%; text-align: right;">Rate</th>
              <th style="width: 8%; text-align: right;">Amount</th>
              <th style="width: 10%; text-align: right;">Disc Amt</th>
              <th style="width: 7%; text-align: right;">T.O Rate</th>
              <th style="width: 8%; text-align: right;">T.O Amt</th>
              <th style="width: 7%; text-align: right;">S.Tax Rate</th>
              <th style="width: 8%; text-align: right;">S.Tax Amt</th>
              <th style="width: 10%; text-align: right;">Net Amount</th>
            </tr>
          </thead>
          <tbody>
            {rows_html_str}
          </tbody>
        </table>

        <table style="width: 100%; border: none; border-collapse: collapse; margin-top: 20px;">
          <tr>
            <td style="width: 50%; border: none;"></td>
            <td style="width: 50%; border: none; padding: 0;">
              <table style="width: 100%; border: 1px solid #e5e7eb; background-color: #f9fafb; padding: 12px; font-size: 11px;">
                <tr>
                  <td style="border: none; padding: 4px 0; color: #6b7280; font-weight: 500; width: 50%;">Subtotal:</td>
                  <td style="border: none; padding: 4px 0; color: #1f2937; font-weight: 600; text-align: right; width: 50%;">Rs. {float(subtotal):.2f}</td>
                </tr>
                <tr>
                  <td style="border: none; padding: 4px 0; color: #6b7280; font-weight: 500;">Invoice Sales Tax:</td>
                  <td style="border: none; padding: 4px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(invoice.s_tax):.2f}</td>
                </tr>
                <tr>
                  <td style="border: none; padding: 4px 0; color: #6b7280; font-weight: 500;">Freight charges:</td>
                  <td style="border: none; padding: 4px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(invoice.freight):.2f}</td>
                </tr>
                <tr>
                  <td style="border: none; padding: 4px 0; color: #6b7280; font-weight: 500;">Advance Income Tax:</td>
                  <td style="border: none; padding: 4px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(invoice.adv_income_tax):.2f}</td>
                </tr>
                <tr>
                  <td style="border: none; border-top: 2px dashed #2563eb; padding: 8px 0 0 0; font-weight: bold; color: #2563eb; font-size: 13px;">Grand Total:</td>
                  <td style="border: none; border-top: 2px dashed #2563eb; padding: 8px 0 0 0; font-weight: bold; color: #2563eb; font-size: 13px; text-align: right;">Rs. {float(invoice.net_amount):.2f}</td>
                </tr>
              </table>
            </td>
          </tr>
        </table>

        <div style="text-align: center; margin-top: 50px; font-size: 9px; color: #9ca3af; border-top: 1px solid #e5e7eb; padding-top: 15px;">
          Generated on {generated_time} | KDM POS System | Page 1 of 1
        </div>
      </body>
    </html>
    """
    return html


def _render_purchase_return_pdf(purchase_return, request):
    rows_html = []
    for idx, line in enumerate(purchase_return.line_items.all()):
        item_name = line.item.name if line.item else '—'
        item_code = line.item.code if line.item else '—'
        
        row = f"""
        <tr class="{'even' if idx % 2 == 1 else 'odd'}">
            <td style="text-align: center;">{idx + 1}</td>
            <td>{item_name} ({item_code})</td>
            <td style="text-align: right;">{float(line.carton):.2f}</td>
            <td style="text-align: right;">{float(line.pcs):.2f}</td>
            <td style="text-align: right;">Rs. {float(line.rate):.2f}</td>
            <td style="text-align: right;">Rs. {float(line.amount):.2f}</td>
            <td style="text-align: right;">Rs. {float(line.discount_amount):.2f}</td>
            <td style="text-align: right;">{float(line.to_rate):.2f}%</td>
            <td style="text-align: right;">Rs. {float(line.to_amount):.2f}</td>
            <td style="text-align: right;">{float(line.s_tax_rate):.2f}%</td>
            <td style="text-align: right;">Rs. {float(line.s_tax_amount):.2f}</td>
            <td style="text-align: right; font-weight: bold;">Rs. {float(line.net_amount):.2f}</td>
        </tr>
        """
        rows_html.append(row)

    rows_html_str = "".join(rows_html)
    
    subtotal = sum(line.net_amount for line in purchase_return.line_items.all())
    
    branch_slug = purchase_return.branch.slug if purchase_return.branch else '—'
    company_name = purchase_return.company.name if purchase_return.company else '—'
    
    generated_time = datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p')
    status_color = "#16a34a" if purchase_return.status == 'paid' else "#dc2626"
    
    remarks_row = ""
    if purchase_return.remarks:
        remarks_row = f"""
        <tr>
          <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Remarks:</td>
          <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{purchase_return.remarks}</td>
        </tr>
        """

    supplier_ntn_row = f"""
    <tr>
      <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">NTN:</td>
      <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{purchase_return.ntn}</td>
    </tr>
    """ if purchase_return.ntn else ""

    supplier_gst_row = f"""
    <tr>
      <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">GST No:</td>
      <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{purchase_return.gst_no}</td>
    </tr>
    """ if purchase_return.gst_no else ""

    html = f"""
    <html>
      <head>
        <title>Purchase Return - {purchase_return.purchase_return_code}</title>
        <style>
          body {{ font-family: 'Helvetica', 'Arial', sans-serif; color: #1f2937; padding: 10px; line-height: 1.4; background: #fff; font-size: 10px; }}
          .items-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px; }}
          .items-table th {{ background-color: #1e3a8a; color: white; padding: 8px 10px; text-align: left; font-weight: bold; border: 1px solid #1e3a8a; font-size: 9px; }}
          .items-table td {{ border: 1px solid #e5e7eb; padding: 8px 10px; color: #374151; font-size: 9px; }}
          .items-table tr.even td {{ background-color: #f9fafb; }}
        </style>
      </head>
      <body>
        <table style="width: 100%; border-collapse: collapse; border-bottom: 3px solid #2563eb; margin-bottom: 20px; padding-bottom: 10px;">
          <tr>
            <td style="width: 50%; vertical-align: top; border: none; padding: 0;">
              <div style="font-size: 24px; font-weight: 800; color: #2563eb; text-transform: uppercase;">Purchase Return</div>
              <div style="font-size: 14px; font-weight: 700; margin-top: 6px; color: #1e3a8a;">Code: {purchase_return.purchase_return_code}</div>
              <div style="font-size: 11px; color: #6b7280; margin-top: 2px;">Date: {purchase_return.date}</div>
              {f'<div style="font-size: 11px; color: #6b7280; margin-top: 2px;">Party Inv #: {purchase_return.party_inv_no}</div>' if purchase_return.party_inv_no else ''}
            </td>
            <td style="width: 50%; text-align: right; vertical-align: top; border: none; padding: 0;">
              <div style="font-weight: 800; font-size: 18px; color: #1e3a8a;">{company_name}</div>
              <div style="font-size: 12px; color: #4b5563;">Branch ID: {branch_slug}</div>
            </td>
          </tr>
        </table>

        <table style="width: 100%; border: none; border-collapse: collapse; margin-bottom: 20px;">
          <tr>
            <td style="width: 48%; vertical-align: top; border: none; padding: 0; padding-right: 10px;">
              <table style="width: 100%; border: 1px solid #e5e7eb; background-color: #f9fafb; padding: 12px; font-size: 11px;">
                <tr>
                  <td style="border: none; padding: 0 0 8px 0; font-weight: bold; font-size: 12px; border-bottom: 1px solid #e5e7eb; color: #1f2937; text-transform: uppercase;">Supplier Details</td>
                </tr>
                <tr>
                  <td style="border: none; padding: 6px 0 0 0;">
                    <table style="width: 100%; border: none; font-size: 11px;">
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500; width: 45%;">Name:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right; width: 55%;">{purchase_return.supplier.name}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Payment Status:</td>
                        <td style="border: none; padding: 2px 0; font-weight: 600; text-align: right; color: {status_color}">{purchase_return.status.upper()}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Outstanding Balance:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(purchase_return.balance_amount):.2f}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Credit Limit:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(purchase_return.credit_limit):.2f}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Credit Days:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{purchase_return.credit_days} Days</td>
                      </tr>
                      {supplier_ntn_row}
                      {supplier_gst_row}
                    </table>
                  </td>
                </tr>
              </table>
            </td>
            <td style="width: 48%; vertical-align: top; border: none; padding: 0; padding-left: 10px;">
              <table style="width: 100%; border: 1px solid #e5e7eb; background-color: #f9fafb; padding: 12px; font-size: 11px;">
                <tr>
                  <td style="border: none; padding: 0 0 8px 0; font-weight: bold; font-size: 12px; border-bottom: 1px solid #e5e7eb; color: #1f2937; text-transform: uppercase;">Ledger Details</td>
                </tr>
                <tr>
                  <td style="border: none; padding: 6px 0 0 0;">
                    <table style="width: 100%; border: none; font-size: 11px;">
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500; width: 45%;">Ledger Account:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right; width: 55%;">{purchase_return.account.name}</td>
                      </tr>
                      {remarks_row}
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>

        <table class="items-table">
          <thead>
            <tr>
              <th style="width: 4%; text-align: center;">S.No</th>
              <th style="width: 24%;">Item Name</th>
              <th style="width: 8%; text-align: right;">Carton</th>
              <th style="width: 8%; text-align: right;">Pcs</th>
              <th style="width: 8%; text-align: right;">Rate</th>
              <th style="width: 8%; text-align: right;">Amount</th>
              <th style="width: 10%; text-align: right;">Disc Amt</th>
              <th style="width: 7%; text-align: right;">T.O Rate</th>
              <th style="width: 8%; text-align: right;">T.O Amt</th>
              <th style="width: 7%; text-align: right;">S.Tax Rate</th>
              <th style="width: 8%; text-align: right;">S.Tax Amt</th>
              <th style="width: 10%; text-align: right;">Net Amount</th>
            </tr>
          </thead>
          <tbody>
            {rows_html_str}
          </tbody>
        </table>

        <table style="width: 100%; border: none; border-collapse: collapse; margin-top: 20px;">
          <tr>
            <td style="width: 50%; border: none;"></td>
            <td style="width: 50%; border: none; padding: 0;">
              <table style="width: 100%; border: 1px solid #e5e7eb; background-color: #f9fafb; padding: 12px; font-size: 11px;">
                <tr>
                  <td style="border: none; padding: 4px 0; color: #6b7280; font-weight: 500; width: 50%;">Subtotal:</td>
                  <td style="border: none; padding: 4px 0; color: #1f2937; font-weight: 600; text-align: right; width: 50%;">Rs. {float(subtotal):.2f}</td>
                </tr>
                <tr>
                  <td style="border: none; padding: 4px 0; color: #6b7280; font-weight: 500;">Invoice Sales Tax:</td>
                  <td style="border: none; padding: 4px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(purchase_return.s_tax):.2f}</td>
                </tr>
                <tr>
                  <td style="border: none; padding: 4px 0; color: #6b7280; font-weight: 500;">Freight charges:</td>
                  <td style="border: none; padding: 4px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(purchase_return.freight):.2f}</td>
                </tr>
                <tr>
                  <td style="border: none; padding: 4px 0; color: #6b7280; font-weight: 500;">Advance Income Tax:</td>
                  <td style="border: none; padding: 4px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(purchase_return.adv_income_tax):.2f}</td>
                </tr>
                <tr>
                  <td style="border: none; border-top: 2px dashed #2563eb; padding: 8px 0 0 0; font-weight: bold; color: #2563eb; font-size: 13px;">Grand Total:</td>
                  <td style="border: none; border-top: 2px dashed #2563eb; padding: 8px 0 0 0; font-weight: bold; color: #2563eb; font-size: 13px; text-align: right;">Rs. {float(purchase_return.net_amount):.2f}</td>
                </tr>
              </table>
            </td>
          </tr>
        </table>

        <div style="text-align: center; margin-top: 50px; font-size: 9px; color: #9ca3af; border-top: 1px solid #e5e7eb; padding-top: 15px;">
          Generated on {generated_time} | KDM POS System | Page 1 of 1
        </div>
      </body>
    </html>
    """
    return html


def _render_damage_return_pdf(damage_return, request):
    rows_html = []
    for idx, line in enumerate(damage_return.line_items.all()):
        item_name = line.item.name if line.item else '—'
        item_code = line.item.code if line.item else '—'
        
        row = f"""
        <tr class="{'even' if idx % 2 == 1 else 'odd'}">
            <td style="text-align: center;">{idx + 1}</td>
            <td>{item_name} ({item_code})</td>
            <td style="text-align: right;">{float(line.carton):.2f}</td>
            <td style="text-align: right;">{float(line.pcs):.2f}</td>
            <td style="text-align: right;">Rs. {float(line.rate):.2f}</td>
            <td style="text-align: right;">Rs. {float(line.amount):.2f}</td>
            <td style="text-align: right;">{float(line.s_tax_rate):.2f}%</td>
            <td style="text-align: right;">Rs. {float(line.s_tax_amount):.2f}</td>
            <td style="text-align: right; font-weight: bold;">Rs. {float(line.net_amount):.2f}</td>
        </tr>
        """
        rows_html.append(row)

    rows_html_str = "".join(rows_html)
    
    subtotal = sum(line.net_amount for line in damage_return.line_items.all())
    
    branch_slug = damage_return.branch.slug if damage_return.branch else '—'
    company_name = damage_return.company.name if damage_return.company else '—'
    
    generated_time = datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p')
    status_color = "#16a34a" if damage_return.status == 'paid' else "#dc2626"
    
    remarks_row = ""
    if damage_return.remarks:
        remarks_row = f"""
        <tr>
          <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Remarks:</td>
          <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{damage_return.remarks}</td>
        </tr>
        """

    supplier_ntn_row = f"""
    <tr>
      <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">NTN:</td>
      <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{damage_return.ntn}</td>
    </tr>
    """ if damage_return.ntn else ""

    supplier_gst_row = f"""
    <tr>
      <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">GST No:</td>
      <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{damage_return.gst_no}</td>
    </tr>
    """ if damage_return.gst_no else ""

    html = f"""
    <html>
      <head>
        <title>Damage Return - {damage_return.damage_return_code}</title>
        <style>
          body {{ font-family: 'Helvetica', 'Arial', sans-serif; color: #1f2937; padding: 10px; line-height: 1.4; background: #fff; font-size: 10px; }}
          .items-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px; }}
          .items-table th {{ background-color: #1e3a8a; color: white; padding: 8px 10px; text-align: left; font-weight: bold; border: 1px solid #1e3a8a; font-size: 9px; }}
          .items-table td {{ border: 1px solid #e5e7eb; padding: 8px 10px; color: #374151; font-size: 9px; }}
          .items-table tr.even td {{ background-color: #f9fafb; }}
        </style>
      </head>
      <body>
        <table style="width: 100%; border-collapse: collapse; border-bottom: 3px solid #2563eb; margin-bottom: 20px; padding-bottom: 10px;">
          <tr>
            <td style="width: 50%; vertical-align: top; border: none; padding: 0;">
              <div style="font-size: 24px; font-weight: 800; color: #2563eb; text-transform: uppercase;">Damage Return</div>
              <div style="font-size: 14px; font-weight: 700; margin-top: 6px; color: #1e3a8a;">Code: {damage_return.damage_return_code}</div>
              <div style="font-size: 11px; color: #6b7280; margin-top: 2px;">Date: {damage_return.date}</div>
              {f'<div style="font-size: 11px; color: #6b7280; margin-top: 2px;">Party Inv #: {damage_return.party_inv_no}</div>' if damage_return.party_inv_no else ''}
            </td>
            <td style="width: 50%; text-align: right; vertical-align: top; border: none; padding: 0;">
              <div style="font-weight: 800; font-size: 18px; color: #1e3a8a;">{company_name}</div>
              <div style="font-size: 12px; color: #4b5563;">Branch ID: {branch_slug}</div>
            </td>
          </tr>
        </table>

        <table style="width: 100%; border: none; border-collapse: collapse; margin-bottom: 20px;">
          <tr>
            <td style="width: 48%; vertical-align: top; border: none; padding: 0; padding-right: 10px;">
              <table style="width: 100%; border: 1px solid #e5e7eb; background-color: #f9fafb; padding: 12px; font-size: 11px;">
                <tr>
                  <td style="border: none; padding: 0 0 8px 0; font-weight: bold; font-size: 12px; border-bottom: 1px solid #e5e7eb; color: #1f2937; text-transform: uppercase;">Supplier Details</td>
                </tr>
                <tr>
                  <td style="border: none; padding: 6px 0 0 0;">
                    <table style="width: 100%; border: none; font-size: 11px;">
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500; width: 45%;">Name:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right; width: 55%;">{damage_return.supplier.name}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Payment Status:</td>
                        <td style="border: none; padding: 2px 0; font-weight: 600; text-align: right; color: {status_color}">{damage_return.status.upper()}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Outstanding Balance:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(damage_return.balance_amount):.2f}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Credit Limit:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(damage_return.credit_limit):.2f}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Credit Days:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{damage_return.credit_days} Days</td>
                      </tr>
                      {supplier_ntn_row}
                      {supplier_gst_row}
                    </table>
                  </td>
                </tr>
              </table>
            </td>
            <td style="width: 48%; vertical-align: top; border: none; padding: 0; padding-left: 10px;">
              <table style="width: 100%; border: 1px solid #e5e7eb; background-color: #f9fafb; padding: 12px; font-size: 11px;">
                <tr>
                  <td style="border: none; padding: 0 0 8px 0; font-weight: bold; font-size: 12px; border-bottom: 1px solid #e5e7eb; color: #1f2937; text-transform: uppercase;">Ledger Details</td>
                </tr>
                <tr>
                  <td style="border: none; padding: 6px 0 0 0;">
                    <table style="width: 100%; border: none; font-size: 11px;">
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500; width: 45%;">Ledger Account:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right; width: 55%;">{damage_return.account.name}</td>
                      </tr>
                      {remarks_row}
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>

        <table class="items-table">
          <thead>
            <tr>
              <th style="width: 4%; text-align: center;">S.No</th>
              <th style="width: 32%;">Item Name</th>
              <th style="width: 10%; text-align: right;">Carton</th>
              <th style="width: 10%; text-align: right;">Pcs</th>
              <th style="width: 10%; text-align: right;">Rate</th>
              <th style="width: 10%; text-align: right;">Amount</th>
              <th style="width: 10%; text-align: right;">S.Tax Rate</th>
              <th style="width: 14%; text-align: right;">Net Amount</th>
            </tr>
          </thead>
          <tbody>
            {rows_html_str}
          </tbody>
        </table>

        <table style="width: 100%; border: none; border-collapse: collapse; margin-top: 20px;">
          <tr>
            <td style="width: 50%; border: none;"></td>
            <td style="width: 50%; border: none; padding: 0;">
              <table style="width: 100%; border: 1px solid #e5e7eb; background-color: #f9fafb; padding: 12px; font-size: 11px;">
                <tr>
                  <td style="border: none; border-top: 2px dashed #2563eb; padding: 8px 0 0 0; font-weight: bold; color: #2563eb; font-size: 13px;">Sub Total:</td>
                  <td style="border: none; border-top: 2px dashed #2563eb; padding: 8px 0 0 0; font-weight: bold; color: #2563eb; font-size: 13px; text-align: right;">Rs. {float(subtotal):.2f}</td>
                </tr>
              </table>
            </td>
          </tr>
        </table>

        <div style="text-align: center; margin-top: 50px; font-size: 9px; color: #9ca3af; border-top: 1px solid #e5e7eb; padding-top: 15px;">
          Generated on {generated_time} | KDM POS System | Page 1 of 1
        </div>
      </body>
    </html>
    """
    return html

def _render_sales_return_pdf(sales_return, request):
    rows_html = []
    for idx, line in enumerate(sales_return.line_items.all()):
        item_name = line.item.name if line.item else '—'
        item_code = line.item.code if line.item else '—'
        manual_code = line.manual_code or '—'
        pack = line.item.pack if line.item else 1
        
        # Calculate carton from pcs and pack
        carton = float(line.pcs) / pack if pack > 0 else 0
        
        row = f"""
        <tr class="{'even' if idx % 2 == 1 else 'odd'}">
            <td style="text-align: center;">{idx + 1}</td>
            <td style="text-align: center;">{manual_code}</td>
            <td>{item_name} ({item_code})</td>
            <td style="text-align: right;">{float(pack):.0f}</td>
            <td style="text-align: right;">{carton:.2f}</td>
            <td style="text-align: right;">{float(line.pcs):.2f}</td>
            <td style="text-align: right;">{float(line.issue_units):.2f}</td>
            <td style="text-align: right;">Rs. {float(line.rate):.2f}</td>
            <td style="text-align: right;">{float(line.s_tax_rate):.2f}%</td>
            <td style="text-align: right;">Rs. {float(line.s_tax_amount):.2f}</td>
            <td style="text-align: right;">Rs. {float(line.gross_amount):.2f}</td>
            <td style="text-align: right; font-weight: bold;">Rs. {float(line.net_amount):.2f}</td>
        </tr>
        """
        rows_html.append(row)

    rows_html_str = "".join(rows_html)
    
    subtotal = sum(line.net_amount for line in sales_return.line_items.all())
    
    branch_slug = sales_return.branch.slug if sales_return.branch else '—'
    company_name = sales_return.company.name if sales_return.company else '—'
    salesman_name = sales_return.salesman.name if sales_return.salesman else '—'
    
    generated_time = datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p')
    status_color = "#16a34a" if sales_return.status == 'paid' else "#dc2626"
    
    remarks_row = ""
    if sales_return.remarks:
        remarks_row = f"""
        <tr>
          <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Remarks:</td>
          <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{sales_return.remarks}</td>
        </tr>
        """

    party_ntn_row = f"""
    <tr>
      <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">NTN:</td>
      <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{sales_return.ntn}</td>
    </tr>
    """ if sales_return.ntn else ""

    party_gst_row = f"""
    <tr>
      <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">GST No:</td>
      <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{sales_return.gst_no}</td>
    </tr>
    """ if sales_return.gst_no else ""

    html = f"""
    <html>
      <head>
        <title>Sales Return - {sales_return.sales_return_code}</title>
        <style>
          body {{ font-family: 'Helvetica', 'Arial', sans-serif; color: #1f2937; padding: 10px; line-height: 1.4; background: #fff; font-size: 10px; }}
          .items-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px; }}
          .items-table th {{ background-color: #1e3a8a; color: white; padding: 8px 10px; text-align: left; font-weight: bold; border: 1px solid #1e3a8a; font-size: 9px; }}
          .items-table td {{ border: 1px solid #e5e7eb; padding: 8px 10px; color: #374151; font-size: 9px; }}
          .items-table tr.even td {{ background-color: #f9fafb; }}
        </style>
      </head>
      <body>
        <table style="width: 100%; border-collapse: collapse; border-bottom: 3px solid #2563eb; margin-bottom: 20px; padding-bottom: 10px;">
          <tr>
            <td style="width: 50%; vertical-align: top; border: none; padding: 0;">
              <div style="font-size: 24px; font-weight: 800; color: #2563eb; text-transform: uppercase;">Sales Return</div>
              <div style="font-size: 14px; font-weight: 700; margin-top: 6px; color: #1e3a8a;">Code: {sales_return.sales_return_code}</div>
              <div style="font-size: 11px; color: #6b7280; margin-top: 2px;">Date: {sales_return.date}</div>
            </td>
            <td style="width: 50%; text-align: right; vertical-align: top; border: none; padding: 0;">
              <div style="font-weight: 800; font-size: 18px; color: #1e3a8a;">{company_name}</div>
              <div style="font-size: 12px; color: #4b5563;">Branch ID: {branch_slug}</div>
            </td>
          </tr>
        </table>

        <table style="width: 100%; border: none; border-collapse: collapse; margin-bottom: 20px;">
          <tr>
            <td style="width: 48%; vertical-align: top; border: none; padding: 0; padding-right: 10px;">
              <table style="width: 100%; border: 1px solid #e5e7eb; background-color: #f9fafb; padding: 12px; font-size: 11px;">
                <tr>
                  <td style="border: none; padding: 0 0 8px 0; font-weight: bold; font-size: 12px; border-bottom: 1px solid #e5e7eb; color: #1f2937; text-transform: uppercase;">Customer Details</td>
                </tr>
                <tr>
                  <td style="border: none; padding: 6px 0 0 0;">
                    <table style="width: 100%; border: none; font-size: 11px;">
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500; width: 45%;">Name:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right; width: 55%;">{sales_return.party.name}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Payment Status:</td>
                        <td style="border: none; padding: 2px 0; font-weight: 600; text-align: right; color: {status_color}">{sales_return.status.upper()}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Outstanding Balance:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(sales_return.balance_amount):.2f}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Credit Limit:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">Rs. {float(sales_return.credit_limit):.2f}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Credit Days:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{sales_return.credit_days} Days</td>
                      </tr>
                      {party_ntn_row}
                      {party_gst_row}
                    </table>
                  </td>
                </tr>
              </table>
            </td>
            <td style="width: 48%; vertical-align: top; border: none; padding: 0; padding-left: 10px;">
              <table style="width: 100%; border: 1px solid #e5e7eb; background-color: #f9fafb; padding: 12px; font-size: 11px;">
                <tr>
                  <td style="border: none; padding: 0 0 8px 0; font-weight: bold; font-size: 12px; border-bottom: 1px solid #e5e7eb; color: #1f2937; text-transform: uppercase;">Ledger & Salesman Details</td>
                </tr>
                <tr>
                  <td style="border: none; padding: 6px 0 0 0;">
                    <table style="width: 100%; border: none; font-size: 11px;">
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500; width: 45%;">Salesman:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right; width: 55%;">{salesman_name}</td>
                      </tr>
                      <tr>
                        <td style="border: none; padding: 2px 0; color: #6b7280; font-weight: 500;">Ledger Account:</td>
                        <td style="border: none; padding: 2px 0; color: #1f2937; font-weight: 600; text-align: right;">{sales_return.account.name}</td>
                      </tr>
                      {remarks_row}
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>

        <table class="items-table">
          <thead>
            <tr>
              <th style="width: 4%; text-align: center;">S.No</th>
              <th style="width: 8%; text-align: center;">Manual Code</th>
              <th style="width: 20%;">Item Name</th>
              <th style="width: 6%; text-align: right;">Pack</th>
              <th style="width: 8%; text-align: right;">Carton</th>
              <th style="width: 8%; text-align: right;">Qty (Pcs)</th>
              <th style="width: 8%; text-align: right;">Issue Units</th>
              <th style="width: 8%; text-align: right;">Rate</th>
              <th style="width: 7%; text-align: right;">S.Tax Rate</th>
              <th style="width: 8%; text-align: right;">S.Tax Amt</th>
              <th style="width: 8%; text-align: right;">Gross Amt</th>
              <th style="width: 8%; text-align: right;">Net Amount</th>
            </tr>
          </thead>
          <tbody>
            {rows_html_str}
          </tbody>
        </table>

        <table style="width: 100%; border: none; border-collapse: collapse; margin-top: 20px;">
          <tr>
            <td style="width: 50%; border: none;"></td>
            <td style="width: 50%; border: none; padding: 0;">
              <table style="width: 100%; border: 1px solid #e5e7eb; background-color: #f9fafb; padding: 12px; font-size: 11px;">
                <tr>
                  <td style="border: none; padding: 4px 0; color: #6b7280; font-weight: 500; width: 50%;">Total Sales Tax:</td>
                  <td style="border: none; padding: 4px 0; color: #1f2937; font-weight: 600; text-align: right; width: 50%;">Rs. {float(sales_return.s_tax):.2f}</td>
                </tr>
                <tr>
                  <td style="border: none; border-top: 2px dashed #2563eb; padding: 8px 0 0 0; font-weight: bold; color: #2563eb; font-size: 13px;">Grand Total:</td>
                  <td style="border: none; border-top: 2px dashed #2563eb; padding: 8px 0 0 0; font-weight: bold; color: #2563eb; font-size: 13px; text-align: right;">Rs. {float(sales_return.net_amount):.2f}</td>
                </tr>
              </table>
            </td>
          </tr>
        </table>

        <div style="text-align: center; margin-top: 50px; font-size: 9px; color: #9ca3af; border-top: 1px solid #e5e7eb; padding-top: 15px;">
          Generated on {generated_time} | KDM POS System | Page 1 of 1
        </div>
      </body>
    </html>
    """
    return html

# ============== VIEWSETS ==============

class OrderBookerViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    serializer_class = OrderBookerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.organization:
            return OrderBooker.objects.none()

        qs = OrderBooker.objects.filter(organization=user.organization)
        if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
            return qs.filter(branch=user.branch).order_by('name')
        return qs.order_by('name')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class SalesmanViewSet(mixins.CreateModelMixin,
                      mixins.RetrieveModelMixin,
                      mixins.UpdateModelMixin,
                      mixins.ListModelMixin,
                      viewsets.GenericViewSet):
    serializer_class = SalesmanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.organization:
            return Salesman.objects.none()

        qs = Salesman.objects.filter(organization=user.organization)
        if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
            return qs.filter(branch=user.branch).order_by('name')
        return qs.order_by('name')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class PartyViewSet(mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    serializer_class = PartySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.organization:
            return Party.objects.none()

        qs = Party.objects.filter(organization=user.organization)
        
        is_party = self.request.query_params.get('is_party')
        if is_party is not None:
            qs = qs.filter(is_party=is_party.lower() == 'true')
            
        is_supplier = self.request.query_params.get('is_supplier')
        if is_supplier is not None:
            qs = qs.filter(is_supplier=is_supplier.lower() == 'true')

        if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
            return qs.filter(branch=user.branch).order_by('name')
        return qs.order_by('name')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)

    @action(detail=True, methods=['get'])
    def statement(self, request, pk=None):
        party = self.get_object()
        queryset = JournalItem.objects.filter(party=party).select_related('entry').order_by('entry__date', 'entry__created_at')
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(entry__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(entry__date__lte=end_date)
            
        serializer = JournalItemSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AccountOpeningViewSet(mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    serializer_class = AccountOpeningSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.organization:
            return AccountOpening.objects.none()

        qs = AccountOpening.objects.filter(organization=user.organization)
        if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
            return qs.filter(branch=user.branch).order_by('code')
        return qs.order_by('code')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)

    @action(detail=True, methods=['get'])
    def statement(self, request, pk=None):
        account = self.get_object()
        queryset = JournalItem.objects.filter(account=account).select_related('entry').order_by('entry__date', 'entry__created_at')
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(entry__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(entry__date__lte=end_date)
            
        serializer = JournalItemSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SalesInvoiceViewSet(mixins.CreateModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.UpdateModelMixin,
                          mixins.ListModelMixin,
                          viewsets.GenericViewSet):
    serializer_class = SalesInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.organization:
            return SalesInvoice.objects.none()

        qs = SalesInvoice.objects.filter(organization=user.organization)
        if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
            return qs.filter(branch=user.branch).order_by('-created_at')
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)

    @action(detail=True, methods=['post'], url_path='change-status')
    def change_status(self, request, pk=None):
        invoice = self.get_object()
        new_status = request.data.get('status')
        if new_status not in ['pending', 'paid']:
            return Response({"error": "Invalid status. Must be 'pending' or 'paid'."}, status=status.HTTP_400_BAD_REQUEST)
            
        if invoice.status == new_status:
            return Response({"message": f"Invoice status is already '{new_status}'."}, status=status.HTTP_200_OK)
            
        with transaction.atomic():
            old_status = invoice.status
            invoice.status = new_status
            invoice.save()
            
            party = invoice.party
            if old_status == 'pending' and new_status == 'paid':
                party.balance_amount -= invoice.net_amount
                pay_entry = JournalEntry.objects.create(
                    organization=invoice.organization,
                    branch=invoice.branch,
                    date=invoice.date,
                    description=f"Payment Receipt for Invoice {invoice.sale_code}",
                    reference=f"PAY-{invoice.sale_code}",
                    sales_invoice=invoice
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    account=invoice.account,
                    debit=invoice.net_amount,
                    credit=0.00,
                    description=f"Cash Receipt - Invoice {invoice.sale_code}"
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    party=invoice.party,
                    debit=0.00,
                    credit=invoice.net_amount,
                    description=f"Accounts Receivable Settlement - Invoice {invoice.sale_code}"
                )
            elif old_status == 'paid' and new_status == 'pending':
                party.balance_amount += invoice.net_amount
                JournalEntry.objects.filter(sales_invoice=invoice, reference=f"PAY-{invoice.sale_code}").delete()
            party.save()
            
        serializer = self.get_serializer(invoice)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='download-pdf')
    def download_pdf(self, request, pk=None):
        invoice = self.get_object()
        pdf_type = request.query_params.get('type', 'regular')
        
        html_string = _render_sales_invoice_pdf(invoice, request, pdf_type)
        
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.pisaDocument(io.BytesIO(html_string.encode('utf-8')), pdf_buffer)
        
        if pisa_status.err:
            return HttpResponse('Error generating PDF', status=500)
            
        pdf_buffer.seek(0)
        filename = f"Invoice_{invoice.sale_code}.pdf"
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class PurchaseInvoiceViewSet(mixins.CreateModelMixin,
                             mixins.RetrieveModelMixin,
                             mixins.UpdateModelMixin,
                             mixins.ListModelMixin,
                             viewsets.GenericViewSet):
    serializer_class = PurchaseInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.organization:
            return PurchaseInvoice.objects.none()

        qs = PurchaseInvoice.objects.filter(organization=user.organization)
        if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
            return qs.filter(branch=user.branch).order_by('-created_at')
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)

    @action(detail=True, methods=['post'], url_path='change-status')
    def change_status(self, request, pk=None):
        invoice = self.get_object()
        new_status = request.data.get('status')
        if new_status not in ['pending', 'paid']:
            return Response({"error": "Invalid status. Must be 'pending' or 'paid'."}, status=status.HTTP_400_BAD_REQUEST)
            
        if invoice.status == new_status:
            return Response({"message": f"Invoice status is already '{new_status}'."}, status=status.HTTP_200_OK)
            
        with transaction.atomic():
            old_status = invoice.status
            invoice.status = new_status
            invoice.save()
            
            supplier = invoice.supplier
            if old_status == 'pending' and new_status == 'paid':
                supplier.balance_amount -= invoice.net_amount
                pay_entry = JournalEntry.objects.create(
                    organization=invoice.organization,
                    branch=invoice.branch,
                    date=invoice.date,
                    description=f"Payment Settlement for Purchase {invoice.purchase_code}",
                    reference=f"PAY-{invoice.purchase_code}",
                    purchase_invoice=invoice
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    party=invoice.supplier,
                    debit=invoice.net_amount,
                    credit=0.00,
                    description=f"Accounts Payable Settlement - Invoice {invoice.purchase_code}"
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    account=invoice.account,
                    debit=0.00,
                    credit=invoice.net_amount,
                    description=f"Cash Paid - Invoice {invoice.purchase_code}"
                )
            elif old_status == 'paid' and new_status == 'pending':
                supplier.balance_amount += invoice.net_amount
                JournalEntry.objects.filter(purchase_invoice=invoice, reference=f"PAY-{invoice.purchase_code}").delete()
            supplier.save()
            
        serializer = self.get_serializer(invoice)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='download-pdf')
    def download_pdf(self, request, pk=None):
        invoice = self.get_object()
        
        html_string = _render_purchase_invoice_pdf(invoice, request)
        
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.pisaDocument(io.BytesIO(html_string.encode('utf-8')), pdf_buffer)
        
        if pisa_status.err:
            return HttpResponse('Error generating PDF', status=500)
            
        pdf_buffer.seek(0)
        filename = f"Invoice_{invoice.purchase_code}.pdf"
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class PurchaseReturnViewSet(mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    serializer_class = PurchaseReturnSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.organization:
            return PurchaseReturn.objects.none()

        qs = PurchaseReturn.objects.filter(organization=user.organization)
        if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
            return qs.filter(branch=user.branch).order_by('-created_at')
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)

    @action(detail=True, methods=['post'], url_path='change-status')
    def change_status(self, request, pk=None):
        purchase_return = self.get_object()
        new_status = request.data.get('status')
        if new_status not in ['pending', 'paid']:
            return Response({"error": "Invalid status. Must be 'pending' or 'paid'."}, status=status.HTTP_400_BAD_REQUEST)
            
        if purchase_return.status == new_status:
            return Response({"message": f"Purchase return status is already '{new_status}'."}, status=status.HTTP_200_OK)
            
        with transaction.atomic():
            old_status = purchase_return.status
            purchase_return.status = new_status
            purchase_return.save()
            
            supplier = purchase_return.supplier
            if old_status == 'pending' and new_status == 'paid':
                supplier.balance_amount += purchase_return.net_amount
                pay_entry = JournalEntry.objects.create(
                    organization=purchase_return.organization,
                    branch=purchase_return.branch,
                    date=purchase_return.date,
                    description=f"Cash Refund for Purchase Return {purchase_return.purchase_return_code}",
                    reference=f"REF-{purchase_return.purchase_return_code}",
                    purchase_return=purchase_return
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    account=purchase_return.account,
                    debit=purchase_return.net_amount,
                    credit=0.00,
                    description=f"Cash Refund Received - Return {purchase_return.purchase_return_code}"
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    party=purchase_return.supplier,
                    debit=0.00,
                    credit=purchase_return.net_amount,
                    description=f"Supplier Refund Settlement - Return {purchase_return.purchase_return_code}"
                )
            elif old_status == 'paid' and new_status == 'pending':
                supplier.balance_amount -= purchase_return.net_amount
                JournalEntry.objects.filter(purchase_return=purchase_return, reference=f"REF-{purchase_return.purchase_return_code}").delete()
            supplier.save()
            
        serializer = self.get_serializer(purchase_return)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='download-pdf')
    def download_pdf(self, request, pk=None):
        purchase_return = self.get_object()
        
        html_string = _render_purchase_return_pdf(purchase_return, request)
        
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.pisaDocument(io.BytesIO(html_string.encode('utf-8')), pdf_buffer)
        
        if pisa_status.err:
            return HttpResponse('Error generating PDF', status=500)
            
        pdf_buffer.seek(0)
        filename = f"PurchaseReturn_{purchase_return.purchase_return_code}.pdf"
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class DamageReturnViewSet(mixins.CreateModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.UpdateModelMixin,
                          mixins.ListModelMixin,
                          viewsets.GenericViewSet):
    serializer_class = DamageReturnSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.organization:
            return DamageReturn.objects.none()

        qs = DamageReturn.objects.filter(organization=user.organization)
        if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
            return qs.filter(branch=user.branch).order_by('-created_at')
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)

    @action(detail=True, methods=['post'], url_path='change-status')
    def change_status(self, request, pk=None):
        damage_return = self.get_object()
        new_status = request.data.get('status')
        if new_status not in ['pending', 'paid']:
            return Response({"error": "Invalid status. Must be 'pending' or 'paid'."}, status=status.HTTP_400_BAD_REQUEST)
            
        if damage_return.status == new_status:
            return Response({"message": f"Damage return status is already '{new_status}'."}, status=status.HTTP_200_OK)
            
        with transaction.atomic():
            old_status = damage_return.status
            damage_return.status = new_status
            damage_return.save()
            
            supplier = damage_return.supplier
            if old_status == 'pending' and new_status == 'paid':
                supplier.balance_amount += damage_return.net_amount
                pay_entry = JournalEntry.objects.create(
                    organization=damage_return.organization,
                    branch=damage_return.branch,
                    date=damage_return.date,
                    description=f"Cash Refund for Damage Return {damage_return.damage_return_code}",
                    reference=f"REF-{damage_return.damage_return_code}",
                    damage_return=damage_return
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    account=damage_return.account,
                    debit=damage_return.net_amount,
                    credit=0.00,
                    description=f"Cash Refund Received (Damage) - Return {damage_return.damage_return_code}"
                )
                JournalItem.objects.create(
                    entry=pay_entry,
                    party=damage_return.supplier,
                    debit=0.00,
                    credit=damage_return.net_amount,
                    description=f"Supplier Refund Settlement (Damage) - Return {damage_return.damage_return_code}"
                )
            elif old_status == 'paid' and new_status == 'pending':
                supplier.balance_amount -= damage_return.net_amount
                JournalEntry.objects.filter(damage_return=damage_return, reference=f"REF-{damage_return.damage_return_code}").delete()
            supplier.save()
            
        serializer = self.get_serializer(damage_return)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='download-pdf')
    def download_pdf(self, request, pk=None):
        damage_return = self.get_object()
        
        html_string = _render_damage_return_pdf(damage_return, request)
        
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.pisaDocument(io.BytesIO(html_string.encode('utf-8')), pdf_buffer)
        
        if pisa_status.err:
            return HttpResponse('Error generating PDF', status=500)
            
        pdf_buffer.seek(0)
        filename = f"DamageReturn_{damage_return.damage_return_code}.pdf"
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


# ============== SALES RETURN VIEWSET ==============

# ============== SALES RETURN VIEWSET ==============

class SalesReturnViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    serializer_class = SalesReturnSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.organization:
            return SalesReturn.objects.none()

        qs = SalesReturn.objects.filter(organization=user.organization)
        if user.role in ['BRANCH_ADMIN', 'USER', 'KPO']:
            return qs.filter(branch=user.branch).order_by('-created_at')
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)

    @action(detail=True, methods=['post'], url_path='change-status')
    def change_status(self, request, pk=None):
        sales_return = self.get_object()
        new_status = request.data.get('status')
        if new_status not in ['pending', 'paid']:
            return Response(
                {"error": "Invalid status. Must be 'pending' or 'paid'."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if sales_return.status == new_status:
            return Response(
                {"message": f"Sales return status is already '{new_status}'."}, 
                status=status.HTTP_200_OK
            )
            
        with transaction.atomic():
            old_status = sales_return.status
            sales_return.status = new_status
            sales_return.save()
            
            party = sales_return.party
            
            if old_status == 'pending' and new_status == 'paid':
                party.balance_amount += sales_return.net_amount
                
                pay_entry = JournalEntry.objects.create(
                    organization=sales_return.organization,
                    branch=sales_return.branch,
                    date=sales_return.date,
                    description=f"Cash Refund for Sales Return {sales_return.sales_return_code}",
                    reference=f"REF-{sales_return.sales_return_code}",
                    sales_invoice=None,
                    purchase_invoice=None,
                    purchase_return=None,
                    damage_return=None,
                    sales_return=None
                )
                
                JournalItem.objects.create(
                    entry=pay_entry,
                    account=sales_return.account,
                    debit=sales_return.net_amount,
                    credit=0.00,
                    description=f"Cash Refund Paid - Return {sales_return.sales_return_code}"
                )
                
                JournalItem.objects.create(
                    entry=pay_entry,
                    party=sales_return.party,
                    debit=0.00,
                    credit=sales_return.net_amount,
                    description=f"Customer Refund Settlement - Return {sales_return.sales_return_code}"
                )
                
            elif old_status == 'paid' and new_status == 'pending':
                party.balance_amount -= sales_return.net_amount
                JournalEntry.objects.filter(
                    sales_return=sales_return, 
                    reference=f"REF-{sales_return.sales_return_code}"
                ).delete()
                
            party.save()
            
        serializer = self.get_serializer(sales_return)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='download-pdf', permission_classes=[AllowAny])  # ✅ Add AllowAny
    def download_pdf(self, request, pk=None):
        sales_return = self.get_object()
        
        html_string = _render_sales_return_pdf(sales_return, request)
        
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.pisaDocument(io.BytesIO(html_string.encode('utf-8')), pdf_buffer)
        
        if pisa_status.err:
            return HttpResponse('Error generating PDF', status=500)
            
        pdf_buffer.seek(0)
        filename = f"SalesReturn_{sales_return.sales_return_code}.pdf"
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response