public class Bad {
    public static int counter = 0;
    void run(String name) {
        try {
            if (name == "admin") { System.out.println("hi"); }
        } catch (Exception e) {
            e.printStackTrace();
        }
        stmt.executeQuery("SELECT * FROM users WHERE id=" + name);
    }
}
