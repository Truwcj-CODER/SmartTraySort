# kotlinx.serialization sinh serializer bang cach doc annotation luc bien dich,
# nhung van tra cuu lai bang ten luc chay - xoa ten di la app do ngay khi
# doc goi tin dau tien.
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**

-keepclassmembers class vn.hasaki.traysort.data.** {
    *** Companion;
}
-keepclasseswithmembers class vn.hasaki.traysort.data.** {
    kotlinx.serialization.KSerializer serializer(...);
}
-keep,includedescriptorclasses class vn.hasaki.traysort.data.**$$serializer { *; }

# OkHttp keo theo may lop chi dung tren nen tang khac. Khong co cung chay duoc.
-dontwarn okhttp3.internal.platform.**
-dontwarn org.conscrypt.**
-dontwarn org.bouncycastle.**
-dontwarn org.openjsse.**

# ML Kit nap bo doc ma qua reflection.
-keep class com.google.mlkit.** { *; }
-dontwarn com.google.mlkit.**
