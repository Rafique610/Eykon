# Eykon Memory Proguard Rules
-keepattributes *Annotation*
-keepclassmembers class * {
    @androidx.room.TypeConverter *;
}
