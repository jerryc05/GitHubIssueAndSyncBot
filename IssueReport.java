package issue_report;

import java.io.File;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedTransferQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

/**
 * ## How to start
 *
 * ```sh
 * export SCRIPT_PATH="/path/to/bot/main.py"
 * export SQLITE_PATH="/path/to/bot/db.db"
 * # start normally like [java -jar xxx.jar]
 * ```
 */
public class IssueReport {
  static final String SCRIPT_PATH_ENV_NAME = "SCRIPT_PATH";
  static final String SQLITE_PATH_ENV_NAME = "SQLITE_PATH";
  static final String ISSUES_TABLE_NAME = "issues";

  static final String ENV_NOT_FOUND_FMT = "Env var [%s] not found!";
  static final String SQL_URI_NOT_FOUND_FMT = "Sqlite uri [%s] not found!";
  static final String SCRIPT_NOT_FOUND_FMT = "Sqlite uri [%s] not found!";
  static final String INVALID_UNIX_EPOCH_FMT = "Invalud unix epoch [%s]!";
  static final String PY_NOT_FOUND_FMT = "Neither [python3] nor [python] is found!";

  static final ThreadPoolExecutor tpe = new ThreadPoolExecutor(4, Integer.MAX_VALUE, 30, TimeUnit.MINUTES,
      new LinkedTransferQueue<>(), Executors.defaultThreadFactory(), new ThreadPoolExecutor.CallerRunsPolicy());

  static File mScriptFile;
  static ProcessBuilder mPyProcess;
  static Connection mConn;

  String title, body, milestone;
  List<CharSequence> labels, assignees;
  long unixEpoch;

  public static void selfCheck() throws SQLException {
    if (mConn == null) {
      String sqlitePath = System.getenv(SQLITE_PATH_ENV_NAME);

      if (sqlitePath == null || sqlitePath.isBlank())
        throw new IllegalStateException(String.format(ENV_NOT_FOUND_FMT, SQLITE_PATH_ENV_NAME));

      if (!sqlitePath.equals(":memory:") && !(new File(sqlitePath)).exists())
        throw new IllegalStateException(String.format(SQL_URI_NOT_FOUND_FMT, sqlitePath));

      mConn = DriverManager.getConnection("jdbc:sqlite:" + sqlitePath);
    }

    if (mScriptFile == null) {
      String scriptPath = System.getenv(SCRIPT_PATH_ENV_NAME);

      if (scriptPath == null || scriptPath.isBlank())
        throw new IllegalStateException(String.format(ENV_NOT_FOUND_FMT, SCRIPT_PATH_ENV_NAME));

      File scriptFile = new File(scriptPath);
      if (!scriptFile.exists())
        throw new IllegalStateException(String.format(SCRIPT_NOT_FOUND_FMT, scriptPath));

      mScriptFile = scriptFile;
    }

    if (mPyProcess == null) {
      try {
        try {
          if (new ProcessBuilder("python3", "--version").start().waitFor() == 0)
            mPyProcess = new ProcessBuilder("python3");
        } catch (IOException e3) {
          try {
            if (new ProcessBuilder("python", "--version").start().waitFor() == 0)
              mPyProcess = new ProcessBuilder("python");
          } catch (IOException e2) {//
          }
        }
      } catch (InterruptedException e) {
        throw new IllegalStateException(e);
      }

      if (mPyProcess == null) {
        throw new IllegalStateException(PY_NOT_FOUND_FMT);
      } else {
        mPyProcess = mPyProcess.inheritIO();
        try {
          mPyProcess.command().add(mScriptFile.getCanonicalPath());
        } catch (IOException e) {
          e.printStackTrace();
          System.err.println("This exception shall never happen!");
        }
      }
    }
  }

  public void submit() {
    // self check
    {
      try {
        selfCheck();
      } catch (Exception e) {
        e.printStackTrace();
        if (e instanceof SQLException)
          System.err.println("If the error message is \"out of memory\", it probably means no database file is found!");
      }
    }

    tpe.execute(() -> {
      // validate input
      String labelsStr, assigneesStr;
      {
        title = Optional.ofNullable(title).orElse("");
        body = Optional.ofNullable(body).orElse("");
        milestone = Optional.ofNullable(milestone).orElse("");
        labelsStr = Optional.ofNullable(labels).map(x -> String.join("\n", x)).orElse("");
        assigneesStr = Optional.ofNullable(assignees).map(x -> String.join("\n", x)).orElse("");
        if (unixEpoch <= 0)
          withUnixEpoch();
      }

      try (PreparedStatement stmt = mConn.prepareStatement(String.format(
          "insert into %s(title,body,milestone,labels,assignees,unix_epoch) values(?,?,?,?,?,?)", ISSUES_TABLE_NAME))) {
        // _______________1_____2____3_________4______5_________6

        stmt.setString(1, title);
        stmt.setString(2, body);
        stmt.setString(3, milestone);
        stmt.setString(4, labelsStr);
        stmt.setString(5, assigneesStr);
        stmt.setLong(6, unixEpoch);

        stmt.setQueryTimeout(30);
        stmt.executeUpdate();

      } catch (SQLException e) {
        e.printStackTrace();
      }

      try {
        mPyProcess.start();
      } catch (IOException e) {
        e.printStackTrace();
      }
    });
  }

  public IssueReport(String title) {
    this.title = title;
  }

  public IssueReport(Throwable exception, CharSequence bodyNotes) {
    exception = Optional.ofNullable(exception).orElse(new Exception());
    bodyNotes = Optional.ofNullable(bodyNotes).orElse("");

    StringWriter sw = new StringWriter();
    exception.printStackTrace(new PrintWriter(sw));

    this.title = exception.getClass().getName();
    this.body = String.format("<details><summary>Stacktrace:</summary>\n```\n%s```\n</details>\n\n%s", sw.toString(),
        bodyNotes);

  }

  public IssueReport appendBody(String body) {
    this.body = Optional.ofNullable(this.body).orElse("") + body;
    return this;
  }

  public IssueReport withMilestone(String milestone) {
    this.milestone = milestone;
    return this;
  }

  public IssueReport withLabels(List<CharSequence> labels) {
    this.labels = labels;
    return this;
  }

  public IssueReport withAssignees(List<CharSequence> assignees) {
    this.assignees = assignees;
    return this;
  }

  public IssueReport withUnixEpoch(long unixEpoch) {
    if (unixEpoch > 0)
      this.unixEpoch = unixEpoch;
    else {
      (new RuntimeException(String.format(INVALID_UNIX_EPOCH_FMT, unixEpoch))).printStackTrace();
      withUnixEpoch();
    }
    return this;
  }

  public IssueReport withUnixEpoch() {
    this.unixEpoch = Instant.now().getEpochSecond();
    return this;
  }
}