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

public class IssueReport implements AutoCloseable {
  static final String SCRIPT_PATH_ENV_NAME = "SCRIPT_PATH";
  static final String SQLITE_PATH_ENV_NAME = "SQLITE_PATH";
  static final String ISSUES_TABLE_NAME = "issues";

  static final String ENV_NOT_FOUND_FMT = "Env var [%s] not found!";
  static final String SQL_URI_NOT_FOUND_FMT = "Sqlite uri [%s] not found!";
  static final String SCRIPT_NOT_FOUND_FMT = "Sqlite uri [%s] not found!";
  static final String INVALID_UNIX_EPOCH_FMT = "Invalud unix epoch [%s]!";
  static final String PY_NOT_FOUND_FMT = "Neither [python3] nor [python] is found!";
  static final String SCRIPT_SELF_CHECK_FAILED_FMT = "Bot script self check failed!";

  static final ThreadPoolExecutor tpe = new ThreadPoolExecutor(4, Integer.MAX_VALUE, 30, TimeUnit.MINUTES,
      new LinkedTransferQueue<>(), Executors.defaultThreadFactory(), new ThreadPoolExecutor.CallerRunsPolicy());

  static File mScriptFile;
  static ProcessBuilder mPyProcess;
  static Connection mConn;

  String title, body, milestone;
  List<CharSequence> labels, assignees;
  long unixEpoch;
  boolean submitted;

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
          } catch (IOException e2) { //
          }
        }

        if (mPyProcess == null) {
          throw new IllegalStateException(PY_NOT_FOUND_FMT);
        } else {
          mPyProcess = mPyProcess.inheritIO();
          try {
            mPyProcess.command().add(mScriptFile.getCanonicalPath());

            ProcessBuilder selfCheck = new ProcessBuilder().inheritIO();
            selfCheck.command().addAll(mPyProcess.command());
            selfCheck.command().add("-c");

            if (selfCheck.start().waitFor() != 0)
              throw new IllegalStateException(SCRIPT_SELF_CHECK_FAILED_FMT);
          } catch (IOException e) {
            throw new IllegalStateException("This shall never happen!", e);
          }
        }
      } catch (InterruptedException e) {
        throw new IllegalStateException(e);
      }
    }
  }

  private void submitUnchecked() {
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

  public void submit() {
    if (!submitted) {
      try {
        selfCheck();
      } catch (Exception e) {
        e.printStackTrace();
        if (e instanceof SQLException)
          System.err.println("If the error message is \"out of memory\", it probably means no database file is found!");
      }

      submitUnchecked();
      submitted = true;

    } else {
      throw new IllegalStateException("Issue already submitted!");
    }
  }

  public void close() {
    try {
      submit();
    } catch (IllegalStateException e) { //
    }
  }

  protected void finalize() throws Throwable {
    try {
      submit();
    } catch (IllegalStateException e) { //
    }
    super.finalize();
  }

  public IssueReport(String title) {
    this.title = title;
    withUnixEpoch();
  }

  public IssueReport(Throwable exception) {
    exception = Optional.ofNullable(exception).orElse(new Exception());

    StringWriter sw = new StringWriter();
    exception.printStackTrace(new PrintWriter(sw));

    title = exception.getClass().getName();
    appendBody(String.format("Stacktrace:\n```\n%s```\n\n", sw.toString()));
    withUnixEpoch();
  }

  public IssueReport appendBody(String body) {
    this.body = String.format("%s%s\n", Optional.ofNullable(this.body).orElse(""), body);
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