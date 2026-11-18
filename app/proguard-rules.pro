# Readable crash traces, without the original file names
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile

# No log lines in the release build, ever (none are written today; this keeps it so)
-assumenosideeffects class android.util.Log {
    public static int v(...);
    public static int d(...);
    public static int i(...);
    public static int w(...);
    public static int e(...);
    public static int wtf(...);
    public static int println(...);
    public static boolean isLoggable(...);
}

# Native code calls back into these classes by name: they keep their names and members
-keep class com.github.luben.zstd.** { *; }
-keep class androidx.sqlite.driver.bundled.** { *; }
-keep class androidx.sqlite.SQLiteException { *; }
