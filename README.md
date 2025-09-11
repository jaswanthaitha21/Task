Extract all possible key-value pairs from the given invoice text. 
Return the result strictly in valid JSON format with the following structure if available:
{
  "invoice": {
    "client_name": "",
    "client_address": "",
    "seller_name": "",
    "seller_address": "",
    "invoice_number": "",
    "invoice_date": "",
    "due_date": ""
  },
  "items": [
    {
      "description": "",
      "quantity": "",
      "total_price": ""
    }
  ],
  "subtotal": {
    "tax": "",
    "discount": "",
    "total": ""
  },
  "payment_instructions": {
    "due_date": "",
    "bank_name": "",
    "account_number": "",
    "payment_method": ""
  }
}
If any field is missing, return it as an empty string.
