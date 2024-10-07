# Copilot Review

Provides a simple HTTP API to interface with GitHub Copilot, including native GitHub authentication.

## Installing dependencies

`pip install -r requirements.txt`

## Run

```sh
cd <your repo>
sh review.sh
```

### Output

```diff
@@ -81,19 +168,36 @@ void find_in_set(sqlite3_context *context, int argc, sqlite3_value **arguments)
+    int *list = (int *)sqlite3_value_blob(arguments[1]);  Potential null pointer dereference if sqlite3_value_blob(arguments[1]) returns NULL. 
```